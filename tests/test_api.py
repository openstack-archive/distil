from webtest import TestApp
import unittest
from api.web import get_app
from sqlalchemy import create_engine
from artifice.models import Resource, Tenant, UsageEntry, SalesOrder
import mock

from sqlalchemy.orm import sessionmaker

master_config = {
 "ceilometer": {
    "host": "http://localhost:8777/"
 }, 
 "main": {
    "export_provider": "artifice.plugins.csv_:Csv",
    "database_uri": "postgres://artifice:password@localhost:5432/artifice"
 }, 
 "openstack": {
    "username": "admin", 
    "authentication_url": "http://localhost:35357/v2.0", 
    "password": "openstack", 
    "default_tenant": "demo"
 }, 
 "export_config": {
      "output_path": "./", 
      "delimiter": ",", 
      "output_file": "%(tenant)s-%(start)s-%(end)s.csv", 
      "rates": {
         "file": "/etc/artifice/csv_rates.csv"
      }
   }
}

# We'll need to grab fixtures and mock out most of the backend stuff.
# again.
#

TENANTS = [
    {u'enabled': True,
     u'description': None,
     u'name': u'demo',
     u'id': u'931dc699f9934021bb4a2b1088ba4d3b',
     "data": {}},

    {u'enabled': True,
     u'description': None,
     u'name': u'tester',
     u'id': u'achoovian',
     "data": {}}
]

DATACENTRE = "testcenter"

import os
try:
    fn = os.path.abspath(__file__)
    path, f = os.path.split(fn)
except NameError:
    path = os.getcwd()


fh = open(os.path.join(path, "data/resources.json"))
resources = json.loads(
        fh.read(),
        parse_float=decimal.Decimal )
fh.close()

i = 0

mappings = {}

i = 0
while True:
    try:
        fh = open(os.path.join(path, "data/map_fixture_%s.json" % i))
        d = json.loads(fh.read(), parse_float=decimal.Decimal)
        fh.close()
        mappings.update(d)
        i += 1
    except IOError:
        break

hosts = set([resource["metadata"]["host"] for resource
             in resources if resource["metadata"].get("host")]),


def get_usage(tenant, start, end):
    pass

class TestApi(unittest.TestCase):

    def setUp(self):
        self.db = sessionmaker( create_engine(master_config["main"]["database_uri"]) )
        self.app = TestApp( get_app(master_config) )

        # Set up the datasets now, based on our
        # original fixtures.

        self.data = {
                "tenants" : TENANTS
        }
         
    def tearDown(self):
        # self.db.execute()
        self.app = None
    
    # Modify Artifice, the Ceilometer client
    @mock.patch("artifice.interface.Artifice")
    @mock.patch("ceilometerclient.v2_0.ResourceManager")
    def test_usage_run_for_all(self, artifice):
        """Asserts a usage run generates data for all tenants"""
        
        tenant_objs =[
                interface.Tenant(t) for t in TENANTS
        ]

        def get_usage(tenant, start, end):
            global mappings
            for url in mappings.keys():
                pass
        for tenant in tenant_objs:
            tenant.usage = mock.Mock(
                    return_value=get_usage(tenant))

        artifice.tenants.return_value = tenant_objs
        
        resp = self.app.post("/collect_usage", dict(tenants=[]))
        self.assertEquals(resp.status_int, 201)
        
        tenants = self.db.query(models.Tenants)
        self.assertTrue ( len(tenants) > 0 )
        for tenant in tenants:
            self.assertEqual(   
                len( tenant.usages ) == \
                len(self.data["tenants"][tenant]["resources"])  )
        usages = self.db.query(models.UsageEntry)

    def test_usage_run_single(self):
        """Asserts a usage run generates one tenant only"""

        tenants = self.data["tenants"].keys()
        self.tenant = tenants[random.randrange(0, len(tenants))]

        resp = self.app.post("/collect_usage", dict(tenants=[tenant]))

        self.assertEquals(resp.status_int, 201)
        
        tenants = self.db.query(Tenants).filter(Tenants.id == self.tenant)
        self.assertTrue( len(tenants) == 1 )

        usages = self.db.query(UsageEntry)
        # Should be one usage per 
        self.assertTrue(len(usage) == len(self.data["tenants"][self.tenant]["resources"]))

    def test_sales_run_for_all(self):
        """"Assertion that a sales run generates all tenant information"""
        # We need to set up the usage information first

        self.test_usage_run_for_all()
        resp = self.app.post("/", dict(tenants=[]))
        self.assertEquals(resp.status_int, 201)
        
        tenants = self.db.query(Tenants)
        for tenant in tenants:
            self.assertTrue(len( tenant.orders ) == 1) # One sales order only

    def test_sales_run_single(self):
        """Assertion that a sales run generates one tenant only"""

        self.test_usage_run_for_single()
        resp = self.app.post("/generate_sales_order", dict(tenants=[self.tenant]))

        self.assertEquals(resp.status_int, 201)
        
        tenant = self.db.query(Tenants).get(self.tenant)
        order_count = self.db.query(SalesOrders).count()
        self.assertEqual(order_count, 1)
    
    def test_no_usage_body_raises_403(self):
        """Assertion that no body on usage request raises 403"""
        resp = self.app.post("/collect_usage")
        self.assertTrue(resp.status_int, 403)

    def test_no_sales_body_raises_403(self):
        """Assertion that no body on sales request raises 403"""
        resp = self.app.post("/generate_sales_order")
        self.assertTrue(resp.status_int, 403)
