# Copyright (C) 2014 Catalyst IT Ltd
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

from webtest import TestApp
from distil.tests.unit import test_interface
from distil.tests.unit import utils
from distil.api import web
from distil.api.web import get_app
from distil import models
from distil import interface
from distil import config
from distil.helpers import convert_to
from distil.constants import dawn_of_time
from datetime import datetime
from decimal import Decimal
import json
import mock
import testtools


class TestAPI(test_interface.TestInterface):
    __name__ = 'TestAPI'

    def setUp(self):
        super(TestAPI, self).setUp()
        with mock.patch("distil.api.web.setup_memcache") as setup_memcache:
            self.app = TestApp(get_app(utils.FAKE_CONFIG))

    def tearDown(self):
        super(TestAPI, self).tearDown()
        self.app = None

    @testtools.skip("skip test.")
    def test_usage_run_for_all(self):
        """Asserts a usage run generates data for all tenants"""

        usage = helpers.get_usage(self.start, self.end)

        with mock.patch('distil.interface.Interface') as Interface:

            tenants = []

            for tenant in constants.TENANTS:
                t = mock.Mock(spec=interface.Tenant)
                t.usage.return_value = usage
                t.conn = mock.Mock()
                t.tenant = tenant
                t.id = tenant['id']
                t.name = tenant['name']
                t.description = tenant['description']
                tenants.append(t)

            ceil_interface = mock.Mock(spec=interface.Interface)

            ceil_interface.tenants = tenants

            Interface.return_value = ceil_interface

            # patch to mock out the novaclient call
            with mock.patch('distil.helpers.flavor_name') as flavor_name:
                flavor_name.side_effect = lambda x: x

                resp = self.app.post("/collect_usage")
                self.assertEqual(200, resp.status_int)

                tenants = self.session.query(models.Tenant)
                self.assertTrue(tenants.count() > 0)

                usages = self.session.query(models.UsageEntry)
                self.assertTrue(usages.count() > 0)
                resources = self.session.query(models.Resource)

                self.assertEqual(resources.count(), len(usage.values()))

    @testtools.skip("skip test.")
    def test_memcache_raw_usage(self):
        """Tests that raw usage queries are cached, and returned."""
        numTenants = 1
        numResources = 5

        end = datetime.strptime("2014-08-01", "%Y-%m-%d")

        fake_memcache = {}
        keys = []
        values = []

        def set_mem(key, value):
            keys.append(key)
            values.append(value)
            fake_memcache[key] = value

        def get_mem(key):
            return fake_memcache.get(key)

        utils.init_db(self.session, numTenants, numResources, end)

        with mock.patch("distil.api.web.memcache") as memcache:
            memcache.get.side_effect = get_mem
            memcache.set.side_effect = set_mem
            resp = self.app.get("/get_usage",
                                params={"tenant": "tenant_id_0",
                                        "start": "2014-07-01T00:00:00",
                                        "end": "2014-08-01T00:00:00"})
            self.assertEqual(resp.body, values[0])

            test_string = "this is not a valid computation"
            fake_memcache[keys[0]] = test_string
            resp2 = self.app.get("/get_usage",
                                 params={"tenant": "tenant_id_0",
                                         "start": "2014-07-01T00:00:00",
                                         "end": "2014-08-01T00:00:00"})
            self.assertEqual(1, len(values))
            self.assertEqual(test_string, resp2.body)

    @testtools.skip("skip test.")
    def test_memcache_rated_usage(self):
        """Tests that rated usage queries are cached, and returned."""
        numTenants = 1
        numResources = 5

        end = datetime.strptime("2014-08-01", "%Y-%m-%d")

        fake_memcache = {}
        keys = []
        values = []

        def set_mem(key, value):
            keys.append(key)
            values.append(value)
            fake_memcache[key] = value

        def get_mem(key):
            return fake_memcache.get(key)

        utils.init_db(self.session, numTenants, numResources, end)

        with mock.patch("distil.api.web.memcache") as memcache:
            memcache.get.side_effect = get_mem
            memcache.set.side_effect = set_mem
            resp = self.app.get("/get_rated",
                                params={"tenant": "tenant_id_0",
                                        "start": "2014-07-01T00:00:00",
                                        "end": "2014-08-01T00:00:00"})
            self.assertEqual(resp.body, values[0])

            test_string = "this is not a valid computation"
            fake_memcache[keys[0]] = test_string
            resp2 = self.app.get("/get_rated",
                                 params={"tenant": "tenant_id_0",
                                         "start": "2014-07-01T00:00:00",
                                         "end": "2014-08-01T00:00:00"})
            self.assertEqual(1, len(values))
            self.assertEqual(test_string, resp2.body)

    def test_tenant_dict(self):
        """Checking that the tenant dictionary is built correctly
           based on given entry data."""
        num_resources = 3
        num_services = 2
        volume = 5

        entries = utils.create_usage_entries(num_resources,
                                             num_services, volume)

        tenant = mock.MagicMock()
        tenant.name = "tenant_1"
        tenant.id = "tenant_id_1"

        db = mock.MagicMock()
        db.get_resources.return_value = {
                'resource_id_0': {},
                'resource_id_1': {},
                'resource_id_2': {},
                }

        tenant_dict = web.build_tenant_dict(tenant, entries, db)

        self.assertEqual(num_resources, len(tenant_dict['resources']))
        self.assertEqual("tenant_id_1", tenant_dict['tenant_id'])
        self.assertEqual("tenant_1", tenant_dict['name'])

        for resource in tenant_dict['resources'].values():
            for service in resource['services']:
                self.assertEqual(volume, service['volume'])

    def test_tenant_dict_no_entries(self):
        """Test to ensure that the function handles an
           empty list of entries correctly."""
        entries = []

        tenant = mock.MagicMock()
        tenant.name = "tenant_1"
        tenant.id = "tenant_id_1"

        db = mock.MagicMock()

        tenant_dict = web.build_tenant_dict(tenant, entries, db)

        self.assertEqual(0, len(tenant_dict['resources']))
        self.assertEqual("tenant_id_1", tenant_dict['tenant_id'])
        self.assertEqual("tenant_1", tenant_dict['name'])

    def test_add_cost_to_tenant(self):
        """Checking that the rates are applied correctly,
           and that we get correct total values."""
        volume = 3600
        rate = {'rate': Decimal(0.25), 'unit': 'hour'}

        test_tenant = {
            'resources': {
                'resource_1': {
                    'services': [{'name': 'service_1',
                                  'volume': Decimal(volume),
                                  'unit': 'second'},
                                 {'name': 'service_2',
                                  'volume': Decimal(volume),
                                  'unit': 'second'}]
                },
                'resource_2': {
                    'services': [{'name': 'service_1',
                                  'volume': Decimal(volume),
                                  'unit': 'second'},
                                 {'name': 'service_2',
                                  'volume': Decimal(volume),
                                  'unit': 'second'}]
                }
            }
        }

        service_cost = round(
            convert_to(volume, 'second', rate['unit']) * rate['rate'], 2)
        total_cost = service_cost * 4

        ratesManager = mock.MagicMock()
        ratesManager.rate.return_value = rate

        tenant_dict = web.add_costs_for_tenant(test_tenant, ratesManager)

        self.assertEqual(tenant_dict['total_cost'], str(total_cost))
        for resource in tenant_dict['resources'].values():
            self.assertEqual(resource['total_cost'], str(service_cost * 2))
            for service in resource['services']:
                self.assertEqual(service['volume'],
                                 str(convert_to(volume, 'second',
                                                rate['unit'])))
                self.assertEqual(service['unit'], rate['unit'])
                self.assertEqual(service['cost'], str(service_cost))

    def test_add_cost_to_empty_tenant(self):
        """An empty tenant should not be charged anything,
           nor cause errors."""

        empty_tenant = {'resources': {}}

        ratesManager = mock.MagicMock()

        tenant_dict = web.add_costs_for_tenant(empty_tenant, ratesManager)

        self.assertEqual(tenant_dict['total_cost'], str(0))

    @testtools.skip("skip test.")
    def test_get_last_collected(self):
        """test to ensure last collected api call returns correctly"""
        now = datetime.now()
        self.session.add(models._Last_Run(last_run=now))
        self.session.commit()
        resp = self.app.get("/last_collected")
        resp_json = json.loads(resp.body)
        self.assertEqual(resp_json['last_collected'], str(now))

    @testtools.skip("skip test.")
    def test_get_last_collected_default(self):
        """test to ensure last collected returns correct default value"""
        resp = self.app.get("/last_collected")
        resp_json = json.loads(resp.body)
        self.assertEqual(resp_json['last_collected'], str(dawn_of_time))

    def test_filter_and_group(self):
        usage = [{'source': 'openstack', 'resource_id': 1},
                 {'source': '22c4f150358e4ed287fa51e050d7f024:TrafficAccounting', 'resource_id': 2},
                 {'source': 'fake', 'resource_id': 3},]
        usage_by_resource = {}
        config.main = {'trust_sources':
                       ['openstack', '.{32}:TrafficAccounting']}
        web.filter_and_group(usage, usage_by_resource)

        expected = {1: [{'source': 'openstack', 'resource_id': 1}],
                    2: [{'source':
                         '22c4f150358e4ed287fa51e050d7f024:TrafficAccounting',
                         'resource_id': 2}]}
        self.assertEqual(expected, usage_by_resource)
