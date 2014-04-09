from webtest import TestApp
from . import test_interface, helpers, constants
from artifice.api import web
from artifice.api.web import get_app
from artifice import models
from artifice import interface
from datetime import datetime
import unittest
import json
import mock


class TestApi(test_interface.TestInterface):

    def setUp(self):
        super(TestApi, self).setUp()
        self.app = TestApp(get_app(constants.config))

    def tearDown(self):
        super(TestApi, self).tearDown()
        self.app = None

    @unittest.skip
    def test_usage_run_for_all(self):
        """Asserts a usage run generates data for all tenants"""

        usage = helpers.get_usage(self.start, self.end)

        with mock.patch('artifice.interface.Artifice') as Artifice:

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

            artifice = mock.Mock(spec=interface.Artifice)

            artifice.tenants = tenants

            Artifice.return_value = artifice

            # patch to mock out the novaclient call
            with mock.patch('artifice.helpers.flavor_name') as flavor_name:
                flavor_name.side_effect = lambda x: x

                resp = self.app.post("/collect_usage")
                self.assertEquals(resp.status_int, 200)

                tenants = self.session.query(models.Tenant)
                self.assertTrue(tenants.count() > 0)

                usages = self.session.query(models.UsageEntry)
                self.assertTrue(usages.count() > 0)
                resources = self.session.query(models.Resource)

                self.assertEquals(resources.count(), len(usage.values()))

    def test_sales_run_for_all(self):
        """Assertion that a sales run generates all tenant orders"""
        numTenants = 7
        numResources = 5

        now = datetime.utcnow().\
            replace(hour=0, minute=0, second=0, microsecond=0)
        helpers.fill_db(self.session, numTenants, numResources, now)

        for i in range(numTenants):
            resp = self.app.post("/sales_order",
                                 params=json.dumps({"tenant": "tenant_id_" +
                                                    str(i)}),
                                 content_type='application/json')
            resp_json = json.loads(resp.body)

            query = self.session.query(models.SalesOrder)
            self.assertEquals(query.count(), i + 1)

            self.assertEquals(len(resp_json['resources']), numResources)

    def test_sales_run_single(self):
        """Assertion that a sales run generates one tenant only"""
        numTenants = 5
        numResources = 5

        now = datetime.utcnow().\
            replace(hour=0, minute=0, second=0, microsecond=0)
        helpers.fill_db(self.session, numTenants, numResources, now)
        resp = self.app.post("/sales_order",
                             params=json.dumps({"tenant": "tenant_id_0"}),
                             content_type="application/json")
        resp_json = json.loads(resp.body)

        query = self.session.query(models.SalesOrder)
        self.assertEquals(query.count(), 1)
        # todo: assert things in the response
        self.assertEquals(len(resp_json['resources']), numResources)

    def test_sales_raises_400(self):
        """Assertion that 400 is being thrown if content is not json."""
        resp = self.app.post("/sales_order", expect_errors=True)
        self.assertEquals(resp.status_int, 400)

    def test_sales_order_no_tenant_found(self):
        """Test that if a tenant is provided and not found,
        then we throw an error."""
        resp = self.app.post('/sales_order',
                             expect_errors=True,
                             params=json.dumps({'tenant': 'bogus tenant'}),
                             content_type='application/json')
        self.assertEquals(resp.status_int, 400)

    def test_tenant_dict(self):
        """"""
        num_resources = 3
        num_services = 2
        volume = 5

        entries = helpers.create_usage_entries(num_resources,
                                               num_services, volume)

        tenant = mock.MagicMock()
        tenant.name = "tenant_1"
        tenant.id = "tenant_id_1"

        db = mock.MagicMock()
        db.get_resource_metadata.return_value = {}

        tenant_dict = web.build_tenant_dict(tenant, entries, db)

        self.assertEquals(len(tenant_dict['resources']), num_resources)
        self.assertEquals(tenant_dict['tenant_id'], "tenant_id_1")
        self.assertEquals(tenant_dict['name'], "tenant_1")

        for resource in tenant_dict['resources'].values():
            for service in resource['services']:
                self.assertEquals(service['volume'], volume)

    def test_tenant_dict_no_entries(self):
        """"""
        entries = []

        tenant = mock.MagicMock()
        tenant.name = "tenant_1"
        tenant.id = "tenant_id_1"

        db = mock.MagicMock()
        db.get_resource_metadata.return_value = {}

        tenant_dict = web.build_tenant_dict(tenant, entries, db)

        self.assertEquals(len(tenant_dict['resources']), 0)
        self.assertEquals(tenant_dict['tenant_id'], "tenant_id_1")
        self.assertEquals(tenant_dict['name'], "tenant_1")
