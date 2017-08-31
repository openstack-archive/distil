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
            json.loads(ret.get_data(as_text=True))
        )

    @mock.patch('distil.erp.drivers.odoo.OdooDriver.get_products')
    @mock.patch('odoorpc.ODOO')
    def test_products_get_without_regions(self, mock_odoo,
                                          mock_odoo_get_products):
        mock_odoo_get_products.return_value = []

        ret = self.client.get('/v2/products')

        self.assertEqual({'products': []}, json.loads(ret.get_data(as_text=True)))

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
        self.assertEqual({'products': []}, json.loads(ret.get_data(as_text=True)))

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
        # NOTE(flwang): Based on current data model of usage entry:
        # volume = Column(Numeric(precision=20, scale=2), nullable=False)
        # it's only necessary to test the case of scale=2.
        db_api.usage_add(
            default_project, res_id, {'instance': 100.12}, 'hour',
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
                                'volume': 100.12,
                                'unit': 'hour'
                            }]
                        }
                    }
                }
            },
            json.loads(ret.get_data(as_text=True))
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
            json.loads(ret.get_data(as_text=True))
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

        self.assertEqual(403, json.loads(ret.get_data(as_text=True)).get('error_code'))

    @mock.patch('distil.erp.drivers.odoo.OdooDriver.get_quotations')
    @mock.patch('odoorpc.ODOO')
    def test_quotations_get(self, mock_odoo, mock_get_quotations):
        self.override_config('keystone_authtoken', region_name='region-1')

        default_project = 'tenant_1'
        res_id = 'instance_1'
        today = datetime.utcnow()
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
                'quotations': {today.strftime("%Y-%m-%d"): {}}
            },
            json.loads(ret.get_data(as_text=True))
        )
