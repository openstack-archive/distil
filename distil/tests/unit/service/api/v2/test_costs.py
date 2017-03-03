# Copyright (C) 2017 Catalyst IT Ltd
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import calendar
from datetime import date
import json

import mock

from distil.db.sqlalchemy import models
from distil.service.api.v2 import costs
from distil.tests.unit import base


class TestCostServiceAPI(base.DistilTestCase):
    @mock.patch(
        'distil.db.api.project_get',
        return_value=models.Tenant(id='fake_project_Id', name='fake_project')
    )
    @mock.patch('distil.db.api.usage_get')
    @mock.patch('distil.db.api.resource_get_by_ids')
    @mock.patch('distil.service.api.v2.products.get_products')
    @mock.patch('distil.erp.utils.load_erp_driver')
    def test_get_costs_last_three_month_to_today(self, mock_load_erp,
                                                 mock_get_products,
                                                 mock_resources,
                                                 mock_usage_get,
                                                 mock_project_get):
        end = date.today()
        year = end.year
        month = end.month - 3

        # Get current day of 3 months before.
        if month <= 0:
            year = end.year - 1
            month = end.month + 9

        start = date(year, month, end.day)
        billing_dates = []

        def get_billing_dates(start, end):
            last_day = calendar.monthrange(start.year, start.month)[1]
            bill_date = date(start.year, start.month, last_day)

            while bill_date < end:
                billing_dates.append(str(bill_date))

                year = (bill_date.year + 1 if bill_date.month + 1 > 12 else
                        bill_date.year)
                month = (bill_date.month + 1) % 12 or 12
                last_day = calendar.monthrange(year, month)[1]

                bill_date = date(year, month, last_day)

        get_billing_dates(start, end)

        get_cost_ret = []
        for d in billing_dates:
            get_cost_ret.append({'billing_date': d, 'total_cost': 10})

        erp_driver = mock.Mock()
        mock_load_erp.return_value = erp_driver
        erp_driver.get_costs.return_value = get_cost_ret

        erp_driver.build_service_name_mapping.return_value = {
            'b1.standard': 'Block Storage',
            'n1.network': 'Network'
        }

        mock_usage_get.return_value = [
            models.UsageEntry(
                tenant_id='fake_project_id',
                service='b1.standard',
                unit='byte',
                resource_id='fake_resource_id_1',
                volume=1024 * 1024 * 1024
            ),
            models.UsageEntry(
                tenant_id='fake_project_id',
                service='n1.network',
                unit='hour',
                resource_id='fake_resource_id_2',
                volume=1
            )
        ]

        mock_get_products.return_value = {
            'test_region': {
                'block storage': [
                    {
                        'resource': 'b1.standard',
                        'price': '1.00',
                        'unit': 'gigabyte',
                    }
                ],
                'network': [
                    {
                        'resource': 'n1.network',
                        'price': '2.00',
                        'unit': 'hour',
                    }
                ],
            }
        }

        mock_resources.return_value = [
            models.Resource(
                id='fake_resource_id_1',
                info=json.dumps({"type": "Image", "name": "image1"})
            ),
            models.Resource(
                id='fake_resource_id_2',
                info=json.dumps({"type": "Network", "name": "network2"})
            ),
        ]

        # Call target method.
        cost = costs.get_costs(
            'fake_project_Id',
            str(start),
            str(end),
            region='test_region'
        )

        monthly_cost = cost['cost']

        self.assertEqual(4, len(monthly_cost))
        self.assertEqual(get_cost_ret, monthly_cost[0:3])

        current_mon_info = monthly_cost[3]

        # If start == end, network discount will not be included.
        if end != date(end.year, end.month, 1):
            self.assertEqual(1.0, current_mon_info['total_cost'])

            breakdown = [
                costs.BILLITEM(
                    id=1,
                    resource='Image',
                    count=1,
                    cost=1.0
                ),
                costs.BILLITEM(
                    id=2,
                    resource='Network',
                    count=1,
                    cost=0.0
                )
            ]
        else:
            self.assertEqual(3.0, current_mon_info['total_cost'])

            breakdown = [
                costs.BILLITEM(
                    id=1,
                    resource='Image',
                    count=1,
                    cost=1.0
                ),
                costs.BILLITEM(
                    id=2,
                    resource='Network',
                    count=1,
                    cost=2.0
                )
            ]

        self.assertEqual(
            sorted(breakdown),
            sorted(current_mon_info['breakdown'])
        )

        service_details = {
            'Image': [{
                'name': 'b1.standard',
                'volume': '1.0',
                'unit': 'gigabyte * hour',
                'resource_id': 'fake_resource_id_1',
                'cost': '1.0',
                'rate': '1.00'
            }],
            'Network': [{
                'name': 'n1.network',
                'volume': '1.0',
                'unit': 'hour',
                'resource_id': 'fake_resource_id_2',
                'cost': '2.0',
                'rate': '2.00'
            }]
        }

        self.assertEqual(service_details, current_mon_info['details'])

    @mock.patch(
        'distil.db.api.project_get',
        return_value=models.Tenant(id='fake_project_Id', name='fake_project')
    )
    @mock.patch('distil.erp.utils.load_erp_driver')
    def test_get_history_costs(self, mock_load_erp, mock_project_get):
        today = date.today()
        year = today.year
        month = today.month - 1
        if month <= 0:
            year = year - 1
            month = today.month + 11

        # Get the last day of the last month as the end.
        end = date(year, month, calendar.monthrange(year, month)[1])

        year = today.year
        month = today.month - 3
        if month <= 0:
            year = year - 1
            month = today.month + 9

        # Get current day of three months before as the start.
        start = date(year, month, today.day)

        billing_dates = []

        def get_billing_dates(start, end):
            last_day = calendar.monthrange(start.year, start.month)[1]
            bill_date = date(start.year, start.month, last_day)

            while bill_date <= end:
                billing_dates.append(str(bill_date))

                year = (bill_date.year + 1 if bill_date.month + 1 > 12 else
                        bill_date.year)
                month = (bill_date.month + 1) % 12 or 12
                last_day = calendar.monthrange(year, month)[1]

                bill_date = date(year, month, last_day)

        get_billing_dates(start, end)

        get_cost_ret = []
        for d in billing_dates:
            get_cost_ret.append({'billing_date': d, 'total_cost': 10})

        erp_driver = mock.Mock()
        mock_load_erp.return_value = erp_driver
        erp_driver.get_costs.return_value = get_cost_ret

        # Call target method.
        cost = costs.get_costs(
            'fake_project_Id',
            str(start),
            str(end),
            region='test_region'
        )

        monthly_cost = cost['cost']

        self.assertEqual(3, len(monthly_cost))
        self.assertEqual(get_cost_ret, monthly_cost)

    @mock.patch(
        'distil.db.api.project_get',
        return_value=models.Tenant(id='fake_project_Id', name='fake_project')
    )
    @mock.patch('distil.db.api.usage_get')
    @mock.patch('distil.db.api.resource_get_by_ids')
    @mock.patch('distil.service.api.v2.products.get_products')
    @mock.patch('distil.erp.utils.load_erp_driver')
    def test_get_costs_current_month(self,
                                     mock_load_erp,
                                     mock_get_products,
                                     mock_resources,
                                     mock_usage_get,
                                     mock_project_get):
        end = date.today()
        start = date(end.year, end.month, 1)

        mock_usage_get.return_value = [
            models.UsageEntry(
                tenant_id='fake_project_id',
                service='b1.standard',
                unit='byte',
                resource_id='fake_resource_id_1',
                volume=1024 * 1024 * 1024
            ),
            models.UsageEntry(
                tenant_id='fake_project_id',
                service='n1.network',
                unit='hour',
                resource_id='fake_resource_id_2',
                volume=1
            )
        ]

        mock_get_products.return_value = {
            'test_region': {
                'block storage': [
                    {
                        'resource': 'b1.standard',
                        'price': '1.00',
                        'unit': 'gigabyte',
                    }
                ],
                'network': [
                    {
                        'resource': 'n1.network',
                        'price': '2.00',
                        'unit': 'hour',
                    }
                ],
            }
        }

        erp_driver = mock.Mock()
        mock_load_erp.return_value = erp_driver
        erp_driver.build_service_name_mapping.return_value = {
            'b1.standard': 'Block Storage',
            'n1.network': 'Network'
        }

        mock_resources.return_value = [
            models.Resource(
                id='fake_resource_id_1',
                info=json.dumps({"type": "Image", "name": "image1"})
            ),
            models.Resource(
                id='fake_resource_id_2',
                info=json.dumps({"type": "Network", "name": "network2"})
            ),
        ]

        # Call target method.
        cost = costs.get_costs(
            'fake_project_Id',
            str(start),
            str(end),
            region='test_region'
        )

        monthly_cost = cost['cost']

        self.assertEqual(1, len(monthly_cost))

        current_mon_info = monthly_cost[0]

        # If start == end, network discount will not be included.
        if start != end:
            self.assertEqual(1.0, current_mon_info['total_cost'])

            breakdown = [
                costs.BILLITEM(
                    id=1,
                    resource='Image',
                    count=1,
                    cost=1.0
                ),
                costs.BILLITEM(
                    id=2,
                    resource='Network',
                    count=1,
                    cost=0.0
                )
            ]
        else:
            self.assertEqual(3.0, current_mon_info['total_cost'])

            breakdown = [
                costs.BILLITEM(
                    id=1,
                    resource='Image',
                    count=1,
                    cost=1.0
                ),
                costs.BILLITEM(
                    id=2,
                    resource='Network',
                    count=1,
                    cost=2.0
                )
            ]

        self.assertEqual(
            sorted(breakdown),
            sorted(current_mon_info['breakdown'])
        )

        service_details = {
            'Image': [{
                'name': 'b1.standard',
                'volume': '1.0',
                'unit': 'gigabyte * hour',
                'resource_id': 'fake_resource_id_1',
                'cost': '1.0',
                'rate': '1.00'
            }],
            'Network': [{
                'name': 'n1.network',
                'volume': '1.0',
                'unit': 'hour',
                'resource_id': 'fake_resource_id_2',
                'cost': '2.0',
                'rate': '2.00'
            }]
        }

        self.assertEqual(service_details, current_mon_info['details'])
