
# from artifice.models import usage, tenants, resources
import unittest
import datetime
import mock

class TestInstancing(unittest.TestCase):

    def setUp(self):

        pass

    def tearDown(self):

        pass

    @mock.patch("artifice.models.Session")
    @mock.patch("artifice.interface.keystone")
    @mock.patch("sqlalchemy.create_engine")
    def test_instance_artifice(self, sqlmock, keystone, session):

        """Tests that artifice correctly instances."""
        from artifice.interface import Artifice
        # from artifice.models import usage

        config = {
            "main": {},
            "database": {
                "username": "aurynn",
                "password": "aurynn",
                "host": "localhost",
                "port": "5433",
                "database": "artifice"
            },
            "openstack": {
                "username": "foo",
                "password": "bar",
                "default_tenant":"asdf",
                "authentication_url": "http://foo"
            },
            "ceilometer": {
                "host": 'http://whee'
            },
            "invoices": {
                "plugin": "json"
            }
        }

        a = Artifice(config)
        self.assertTrue( isinstance(a, Artifice) )


    def test_instance_usage(self):

        from artifice.models import usage, tenants, resources

        start = datetime.datetime.now() - datetime.timedelta(days=30)
        end = datetime.datetime.now()

        r = resources.Resource()
        t = tenants.Tenant()
        r.tenant = t
        u = usage.Usage(r, t , 1, start, end )
        self.assertTrue ( isinstance( u, usage.Usage ) )

    def test_instance_tenant(self):

        from artifice.models import tenants

        t = tenants.Tenant()
        self.assertTrue( isinstance(t, tenants.Tenant) )

    def test_instance_resource(self):

        from artifice.models import resources

        r = resources.Resource()
        self.assertTrue( isinstance(r, resources.Resource) )