from . import test_interface
from artifice import database
from artifice.models.db_models import Tenant
import os
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

try:
    fn = os.path.abspath(__file__)
    path, f = os.path.split(fn)
except NameError:
    path = os.getcwd()


class TestInvoice(test_interface.TestInterface):

    def tearDown(self):

        super(TestInvoice, self).tearDown()

    def test_artifice_start_session(self):
        """Loading and instancing the database module works as expected: """
        try:
            db = database.Database(None, self.session)
        except ImportError as e:
            self.fail("Couldn't import: %s" % e)
        return db

    def test_adding_to_db(self):
        """Tests adding all the data to the database."""

        self.test_get_usage()

        db = self.test_artifice_start_session()
        db.enter(self.usage.vms, self.start, self.end)
        db.enter(self.usage.objects, self.start, self.end)
        db.enter(self.usage.networks, self.start, self.end)
        db.enter(self.usage.volumes, self.start, self.end)

    def test_get_from_db_1(self):
        """Test to return a list of billable tenant objects,
           with the 'tenants' parameter as None, which should
           default to all tenants in the tenant table (just demo)."""
        self.test_get_usage()

        db = self.test_artifice_start_session()
        db.enter(self.usage.vms, self.start, self.end)
        db.enter(self.usage.objects, self.start, self.end)
        db.enter(self.usage.networks, self.start, self.end)
        db.enter(self.usage.volumes, self.start, self.end)

        # add a tenant to the tenants table
        db.session.add(Tenant(tenant_id="8a78fa56de8846cb89c7cf3f37d251d5",
                              name="demo", info=""))

        tenants = db.tenants(self.start, self.end)

        self.assertEqual(len(tenants), 1)

        for tenant in tenants:
            print
            print "Billable tenant Object:"
            print "  " + tenant.name
            self.assertEqual(tenant.name, "demo")
            for resource in tenant.resources.values():
                print "    " + str(resource.metadata)
                print "    " + resource.id

                if resource.id == "23dd6f29-754f-41a8-b488-6c0113af272b":
                    strat = resource.usage_strategies["m1.tiny"]
                    self.assertEqual(strat.volume, 6)
                if resource.id == "3d736ab0-3429-43bb-86ef-bba41fffd6ef":
                    strat = resource.usage_strategies["m1.medium"]
                    self.assertEqual(strat.volume, 1)
                if resource.id == "3e3da06d-9a0e-4412-984a-c189dde81377":
                    strat = resource.usage_strategies["m1.tiny"]
                    self.assertEqual(strat.volume, 1)
                if resource.id == "388b3939-8854-4a1b-a133-e738f1ffbb0a":
                    strat = resource.usage_strategies["m1.micro"]
                    self.assertEqual(strat.volume, 1)
                if resource.id == "8a78fa56de8846cb89c7cf3f37d251d5":
                    strat = resource.usage_strategies["storage_size"]
                    self.assertEqual(strat.volume, 180667.463)
                if (resource.id ==
                        "nova-instance-instance-00000001-fa163e915745"):
                    strat = resource.usage_strategies["outgoing_megabytes"]
                    self.assertEqual(strat.volume, 26.134)
                    strat = resource.usage_strategies["incoming_megabytes"]
                    self.assertEqual(strat.volume, 30.499)
                if (resource.id ==
                        "nova-instance-instance-00000004-fa163e99f87f"):
                    strat = resource.usage_strategies["outgoing_megabytes"]
                    self.assertEqual(strat.volume, 8.355)
                    strat = resource.usage_strategies["incoming_megabytes"]
                    self.assertEqual(strat.volume, 7.275)

                for usage in resource.usage_strategies.values():
                    print "      " + usage.service
                    print "      " + str(usage.volume)

        def test_get_from_db_2(self):
            """Test to return a list of billable tenant objects,
               with the 'tenants' parameter given a tuple with the
               resource_id for the demo tenant."""
            self.test_get_usage()

            db = self.test_artifice_start_session()
            db.enter(self.usage.vms, self.start, self.end)
            db.enter(self.usage.objects, self.start, self.end)
            db.enter(self.usage.networks, self.start, self.end)
            db.enter(self.usage.volumes, self.start, self.end)

            db.session.add(Tenant(tenant_id="8a78fa56de8846cb89c7cf3f37d251d5",
                                  name="demo"))

            tenants = db.tenants(self.start, self.end,
                                 ("8a78fa56de8846cb89c7cf3f37d251d5",))

            self.assertEqual(len(tenants), 1)
