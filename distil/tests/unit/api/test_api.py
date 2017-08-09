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
import copy
from datetime import date
from datetime import datetime
import json

from flask import url_for
import mock
from oslo_policy import policy as cpolicy

from distil.api import acl
from distil.common import constants
from distil.db import api as db_api
from distil.tests.unit.api import base

DETAILS_1 = {
    "Compute": {
        "breakdown": {
            "NZ-POR-1.c1.c2r16": [
                {
                    "cost": 339.0,
                    "quantity": 1000,
                    "rate": 0.339,
                    "resource_id": "nz_por_111",
                    "resource_name": "nz_por_111",
                    "unit": "hour"
                }
            ],
        },
        "total_cost": 339.0
    },
    "Network": {
        "breakdown": {
            "NZ-POR-1.n1.network": [
                {
                    # Will be calculated in the test case
                    "cost": 0,
                    "quantity": 0,
                    "rate": 0.0164,
                    "resource_id": "nz_por_222",
                    "resource_name": "nz_por_222",
                    "unit": "hour"
                }
            ],
            "NZ-POR-1.n1.router": [
                {
                    # Will be calculated in the test case
                    "cost": 0,
                    "quantity": 0,
                    "rate": 0.017,
                    "resource_id": "nz_por_333",
                    "resource_name": "nz_por_333",
                    "unit": "hour"
                }
            ],
        },
        "total_cost": 0
    },
    "Object Storage": {
        "breakdown": {
            "NZ-POR-1.o1.standard": [
                {
                    "cost": 27.0,
                    "quantity": 100000,
                    "rate": 0.00027,
                    "resource_id": "object_storage_id",
                    "resource_name": "object_storage_name",
                    "unit": "gigabyte"
                },
            ]
        },
        "total_cost": 27.0
    }
}
DETAILS_2 = {
    "Block Storage": {
        "breakdown": {
            "NZ-WLG-2.b1.standard": [
                {
                    "cost": 5.0,
                    "quantity": 10000,
                    "rate": 0.0005,
                    "resource_id": "nz_wlg_111",
                    "resource_name": "nz_wlg_111",
                    "unit": "gigabyte"
                },
            ]
        },
        "total_cost": 5.0
    },
    "Network": {
        "breakdown": {
            "NZ-WLG-2.n1.network": [
                {
                    "cost": 164.0,
                    "quantity": 10000,
                    "rate": 0.0164,
                    "resource_id": "nz_wlg_222",
                    "resource_name": "nz_wlg_222",
                    "unit": "hour"
                }
            ],
            "NZ-WLG-2.n1.router": [
                {
                    "cost": 17.0,
                    "quantity": 1000,
                    "rate": 0.017,
                    "resource_id": "nz_wlg_333",
                    "resource_name": "nz_wlg_333",
                    "unit": "hour"
                }
            ],
        },
        "total_cost": 181.0
    },
    "Object Storage": {
        "breakdown": {
            "NZ-WLG-2.o1.standard": [
                {
                    "cost": 54.0,
                    "quantity": 200000,
                    "rate": 0.00027,
                    "resource_id": "object_storage_id",
                    "resource_name": "object_storage_name",
                    "unit": "gigabyte"
                },
            ]
        },
        "total_cost": 54.0
    }
}



class TestAPI(base.APITest):
    @classmethod
    def setUpClass(cls):
        acl.setup_policy()

    def _setup_policy(self, policy):
        policy.update(
            {"admin_or_owner": "is_admin:True or project_id:%(project_id)s"}
        )
        rules = cpolicy.Rules.from_dict(policy)
        acl.ENFORCER.set_rules(rules, use_conf=False)

        self.addCleanup(acl.ENFORCER.clear)

    def test_get_versions(self):
        ret = self.client.get('/')

        self.assertEqual(
            {'versions': [{'id': 'v2', 'status': 'CURRENT'}]},
            json.loads(ret.data)
        )

    @mock.patch('distil.erp.drivers.odoo.OdooDriver.get_products')
    @mock.patch('odoorpc.ODOO')
    def test_products_get_without_regions(self, mock_odoo,
                                          mock_odoo_get_products):
        mock_odoo_get_products.return_value = []

        ret = self.client.get('/v2/products')

        self.assertEqual({'products': []}, json.loads(ret.data))

    @mock.patch('distil.erp.drivers.odoo.OdooDriver.get_products')
    @mock.patch('odoorpc.ODOO')
    @mock.patch('distil.common.openstack.get_regions')
    def test_products_get_with_regions(self, mock_regions, mock_odoo,
                                       mock_odoo_get_products):
        class Region(object):
            def __init__(self, id):
                self.id = id

        mock_regions.return_value = [Region('nz_1'), Region('nz_2')]
        mock_odoo_get_products.return_value = []

        ret = self.client.get('/v2/products?regions=nz_1,nz_2')

        mock_odoo_get_products.assert_called_once_with(['nz_1', 'nz_2'])
        self.assertEqual({'products': []}, json.loads(ret.data))

    @mock.patch('distil.common.openstack.get_regions')
    def test_products_get_with_invalid_regions(self, mock_regions):
        class Region(object):
            def __init__(self, id):
                self.id = id

        mock_regions.return_value = [Region('nz_1'), Region('nz_2')]

        ret = self.client.get('/v2/products?regions=nz_1,nz_3')

        self.assertEqual(404, ret.status_code)

    def test_measurements_get(self):
        default_project = 'tenant_1'
        start = '2014-06-01T00:00:00'
        end = '2014-07-01T00:00:00'
        res_id = 'instance_1'

        db_api.project_add(
            {
                'id': default_project,
                'name': 'default_project',
                'description': 'project for test'
            }
        )
        db_api.resource_add(
            default_project, res_id, {'type': 'Virtual Machine'}
        )
        db_api.usage_add(
            default_project, res_id, {'instance': 100}, 'hour',
            datetime.strptime(start, constants.iso_time),
            datetime.strptime(end, constants.iso_time),
        )

        with self.app.test_request_context():
            url = url_for(
                'v2.measurements_get',
                project_id=default_project,
                start=start,
                end=end
            )

        self._setup_policy({"rating:measurements:get": "rule:admin_or_owner"})
        ret = self.client.get(url, headers={'X-Tenant-Id': default_project})

        self.assertEqual(
            {
                'measurements': {
                    'start': '2014-06-01 00:00:00',
                    'end': '2014-07-01 00:00:00',
                    'project_name': 'default_project',
                    'project_id': default_project,
                    'resources': {
                        res_id: {
                            'type': 'Virtual Machine',
                            'services': [{
                                'name': 'instance',
                                'volume': '100.00',
                                'unit': 'hour'
                            }]
                        }
                    }
                }
            },
            json.loads(ret.data)
        )

    @mock.patch('distil.erp.drivers.odoo.OdooDriver.get_invoices')
    @mock.patch('odoorpc.ODOO')
    def test_invoices_get(self, mock_odoo, mock_get_invoices):
        default_project = 'tenant_1'
        start = '2014-06-01T00:00:00'
        end = '2014-07-01T00:00:00'

        db_api.project_add(
            {
                'id': default_project,
                'name': 'default_project',
                'description': 'project for test'
            }
        )

        mock_get_invoices.return_value = {}

        with self.app.test_request_context():
            url = url_for(
                'v2.invoices_get',
                project_id=default_project,
                start=start,
                end=end
            )

        self._setup_policy({"rating:invoices:get": "rule:admin_or_owner"})
        ret = self.client.get(url, headers={'X-Tenant-Id': default_project})

        self.assertEqual(
            {
                'start': '2014-06-01 00:00:00',
                'end': '2014-07-01 00:00:00',
                'project_name': 'default_project',
                'project_id': default_project,
                'invoices': {}
            },
            json.loads(ret.data)
        )

    def test_get_other_project_invoice_not_admin(self):
        default_project = 'tenant_1'
        start = '2014-06-01T00:00:00'
        end = '2014-07-01T00:00:00'

        with self.app.test_request_context():
            url = url_for(
                'v2.invoices_get',
                project_id='other_tenant',
                start=start,
                end=end
            )

        self._setup_policy({"rating:invoices:get": "rule:admin_or_owner"})
        ret = self.client.get(url, headers={'X-Tenant-Id': default_project})

        self.assertEqual(403, json.loads(ret.data).get('error_code'))

    @mock.patch('distil.erp.drivers.odoo.OdooDriver.get_quotations')
    @mock.patch('odoorpc.ODOO')
    def test_quotations_get(self, mock_odoo, mock_get_quotations):
        self.override_config('keystone_authtoken', region_name='region-1')

        default_project = 'tenant_1'
        res_id = 'instance_1'
        today = date.today()
        datetime_today = datetime(today.year, today.month, today.day)

        db_api.project_add(
            {
                'id': default_project,
                'name': 'default_project',
                'description': 'project for test'
            }
        )
        db_api.resource_add(
            default_project, res_id, {'type': 'Virtual Machine'}
        )
        db_api.usage_add(
            default_project, res_id, {'instance': 100}, 'hour',
            datetime_today,
            datetime_today,
        )

        mock_get_quotations.return_value = {}

        with self.app.test_request_context():
            url = url_for(
                'v2.quotations_get',
                project_id=default_project,
            )

        self._setup_policy({"rating:quotations:get": "rule:admin_or_owner"})
        ret = self.client.get(url, headers={'X-Tenant-Id': default_project})

        self.assertEqual(
            {
                'start': str(datetime(today.year, today.month, 1)),
                'end': str(datetime_today),
                'project_name': 'default_project',
                'project_id': default_project,
                'quotations': {str(today): {}}
            },
            json.loads(ret.data)
        )

    @mock.patch(
        'distil.service.api.v2.quotations._get_current_region_quotation'
    )
    @mock.patch('distil.common.openstack.get_regions')
    @mock.patch('distil.common.openstack.get_distil_client')
    def test_quotations_get_all_regions(self, mock_distil, mock_regions,
                                        mock_cur_quotation):
        self.override_config('keystone_authtoken', region_name='region-1')

        class Region(object):
            def __init__(self, name):
                self.id = name

        mock_regions.return_value = [
            Region('region-1'),
            Region('region-2'),
            Region('region-3')
        ]
        distil_client_1 = mock.Mock()
        distil_client_2 = mock.Mock()
        mock_distil.side_effect = [distil_client_1, distil_client_2]

        now = datetime.utcnow()
        start_date = datetime(year=now.year, month=now.month, day=1)
        free_hours = int((now - start_date).total_seconds() / 3600)

        # We intentionally set the network/network quantity to control the
        # discount value.
        network_discount = round(0.0164 * free_hours, 2)
        router_discount = round(0.017 * free_hours, 2)
        detail_1 = copy.deepcopy(DETAILS_1)
        detail_1['Network']['breakdown']['NZ-POR-1.n1.network'][0][
            'quantity'] = free_hours
        detail_1['Network']['breakdown']['NZ-POR-1.n1.network'][0][
            'cost'] = network_discount
        detail_1['Network']['breakdown']['NZ-POR-1.n1.router'][0][
            'quantity'] = free_hours
        detail_1['Network']['breakdown']['NZ-POR-1.n1.router'][0][
            'cost'] = router_discount
        detail_1['Network']['total_cost'] = network_discount + router_discount

        distil_client_1.quotations.list.return_value = {
            'quotations': {
                str(now): {
                    'details': detail_1
                }
            }
        }
        distil_client_2.quotations.list.return_value = {
            'quotations': {
                str(now): {
                    'details': DETAILS_2
                }
            }
        }

        default_project = 'tenant_1'
        today = date.today()
        datetime_today = datetime(today.year, today.month, today.day)

        db_api.project_add(
            {
                'id': default_project,
                'name': 'default_project',
                'description': 'project for test'
            }
        )

        mock_cur_quotation.return_value = {
            'start': str(datetime(today.year, today.month, 1)),
            'end': str(datetime_today),
            'project_id': default_project,
            'project_name': 'default_project',
            'quotations': {
                str(today): {
                    'details': {},
                    'total_cost': 0.0
                }
            }
        }

        self._setup_policy({"rating:quotations:get": "rule:admin_or_owner"})
        with self.app.test_request_context():
            url = url_for(
                'v2.quotations_get',
                project_id=default_project,
                detailed=True,
                all_regions=True
            )
        ret = self.client.get(url, headers={'X-Tenant-Id': default_project})

        final_details = {
            "Compute": {
                "breakdown": {
                    "NZ-POR-1.c1.c2r16": [
                        {
                            "cost": 339.0,
                            "quantity": 1000,
                            "rate": 0.339,
                            "resource_id": "nz_por_111",
                            "resource_name": "nz_por_111",
                            "unit": "hour"
                        }
                    ],
                },
                "total_cost": 339.0
            },
            "Block Storage": {
                "breakdown": {
                    "NZ-WLG-2.b1.standard": [
                        {
                            "cost": 5.0,
                            "quantity": 10000,
                            "rate": 0.0005,
                            "resource_id": "nz_wlg_111",
                            "resource_name": "nz_wlg_111",
                            "unit": "gigabyte"
                        },
                    ]
                },
                "total_cost": 5.0
            },
            "Network": {
                "breakdown": {
                    "NZ-POR-1.n1.network": [
                        {
                            "cost": network_discount,
                            "quantity": free_hours,
                            "rate": 0.0164,
                            "resource_id": "nz_por_222",
                            "resource_name": "nz_por_222",
                            "unit": "hour"
                        }
                    ],
                    "NZ-POR-1.n1.router": [
                        {
                            "cost": router_discount,
                            "quantity": free_hours,
                            "rate": 0.017,
                            "resource_id": "nz_por_333",
                            "resource_name": "nz_por_333",
                            "unit": "hour"
                        }
                    ],
                    "NZ-WLG-2.n1.network": [
                        {
                            "cost": 164.0,
                            "quantity": 10000,
                            "rate": 0.0164,
                            "resource_id": "nz_wlg_222",
                            "resource_name": "nz_wlg_222",
                            "unit": "hour"
                        }
                    ],
                    "NZ-WLG-2.n1.router": [
                        {
                            "cost": 17.0,
                            "quantity": 1000,
                            "rate": 0.017,
                            "resource_id": "nz_wlg_333",
                            "resource_name": "nz_wlg_333",
                            "unit": "hour"
                        }
                    ],
                    "discount.n1.network": [
                        {
                            "cost": -network_discount,
                            "quantity": -free_hours,
                            "rate": 0.0164,
                            "unit": "hour"
                        }
                    ],
                    "discount.n1.router": [
                        {
                            "cost": -router_discount,
                            "quantity": -free_hours,
                            "rate": 0.017,
                            "unit": "hour"
                        }
                    ],
                },
                "total_cost": 181.0
            },
            "Object Storage": {
                "breakdown": {
                    "NZ-WLG-2.o1.standard": [
                        {
                            "cost": 54.0,
                            "quantity": 200000,
                            "rate": 0.00027,
                            "resource_id": "object_storage_id",
                            "resource_name": "object_storage_name",
                            "unit": "gigabyte"
                        },
                    ]
                },
                "total_cost": 54.0
            }
        }

        self.assertEqual(
            {
                'start': str(datetime(today.year, today.month, 1)),
                'end': str(datetime_today),
                'project_name': 'default_project',
                'project_id': default_project,
                'quotations': {
                    str(today): {
                        'details': final_details,
                        'total_cost': 579.0
                    }
                }
            },
            json.loads(ret.data)
        )
