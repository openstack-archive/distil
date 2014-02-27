from webtest import TestApp
from . import test_interface
from api.web import get_app
from artifice import models
from artifice import interface
from datetime import datetime, timedelta
from random import randint
import json
import mock

import unittest


class TestApi(test_interface.TestInterface):

    def setUp(self):
        super(TestApi, self).setUp()
        self.app = TestApp(get_app(test_interface.config))
         
    def tearDown(self):
        super(TestApi, self).tearDown()
        self.app = None

    def fill_db(self, numb_tenants, numb_resources, now):
        for i in range(numb_tenants):
            self.session.add(models.Tenant(
                id="tenant_id_" + str(i),
                info="metadata",
                name="tenant_name_" + str(i),
                created=now
            ))
            for ii in range(numb_resources):
                self.session.add(models.Resource(
                    id="resource_id_" + str(ii),
                    info=json.dumps({"type": "Resource" + str(ii)}),
                    tenant_id="tenant_id_" + str(i),
                    created=now
                ))
                self.session.add(models.UsageEntry(
                    service="service" + str(ii),
                    volume=5,
                    resource_id="resource_id_" + str(ii),
                    tenant_id="tenant_id_" + str(i),
                    start=(now - timedelta(days=30)),
                    end=now,
                    created=now
                ))
        self.session.commit()

    
    # Modify Artifice, the Ceilometer client
    @mock.patch("artifice.interface.keystone")
    def test_usage_run_for_all(self, keystone):
        """Asserts a usage run generates data for all tenants"""
        
        self.test_get_usage()

        with mock.patch('artifice.interface.Artifice') as Artifice:

            tenants = []

            for tenant in test_interface.TENANTS:
                t = mock.Mock(spec=interface.Tenant)
                t.usage.return_value = self.usage
                t.conn = tenant
                tenants.append(t)

            artifice = mock.Mock(spec=interface.Artifice)

            artifice.tenants = tenants

            Artifice.return_value = artifice

            resp = self.app.post("/collect_usage")
            self.assertEquals(resp.status_int, 200)

            tenants = self.session.query(models.Tenant)
            self.assertTrue(tenants.count() > 0)

            usages = self.session.query(models.UsageEntry)
            self.assertTrue(usages.count() > 0)
            resources = self.session.query(models.Resource)
            count = 0
            for res_type in self.usage.values():
                count += len(res_type)
            self.assertEquals(resources.count(), count)

    def test_sales_run_for_all(self):
        """"Assertion that a sales run generates all tenant orders"""

        now = datetime.now().\
            replace(hour=0, minute=0, second=0, microsecond=0)
        self.fill_db(7, 5, now)
        resp = self.app.post("/sales_order")
        resp_json = json.loads(resp.body)

        self.assertEquals(resp.status_int, 200)

        query = self.session.query(models.SalesOrder)
        self.assertEquals(query.count(), 7)

        self.assertEquals(len(resp_json['tenants']), 7)

        i = 0
        for tenant in resp_json['tenants']:
            self.assertTrue(tenant['generated'])
            self.assertEquals(tenant['id'], 'tenant_id_' + str(i))
            i += 1

    def test_sales_run_single(self):
        """Assertion that a sales run generates one tenant only"""

        now = datetime.now().\
            replace(hour=0, minute=0, second=0, microsecond=0)
        self.fill_db(5, 5, now)
        resp = self.app.post("/sales_order",
                             params=json.dumps({"tenants": ["tenant_id_0"]}),
                             content_type="application/json")
        resp_json = json.loads(resp.body)

        self.assertEquals(resp.status_int, 200)

        query = self.session.query(models.SalesOrder)
        self.assertEquals(query.count(), 1)
        # todo: assert things in the response
        self.assertEquals(len(resp_json['tenants']), 1)
        self.assertTrue(resp_json['tenants'][0]['generated'])
        self.assertEquals(resp_json['tenants'][0]['id'], 'tenant_id_0')

    @unittest.skip
    def test_sales_raises_400(self):
        """Assertion that 400 is being thrown if content is not json."""
        resp = self.app.post("/sales_order")
        self.assertTrue(resp.status_int, 400)
