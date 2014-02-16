from . import test_interface
from decimal import Decimal
from artifice import database
from artifice.models import Tenant
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class TestDatabaseModels(test_interface.TestInterface):

    def tearDown(self):

        super(TestDatabaseModels, self).tearDown()

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
        db.enter(self.usage.ips, self.start, self.end)

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
        db.enter(self.usage.ips, self.start, self.end)

        # add a tenant to the tenants table
        db.session.add(Tenant(tenant_id="3f7b702e4ca14cd99aebf4c4320e00ec",
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

                if resource.id == "db8037b2-9f1c-4dd2-94dd-ea72f49a21d7":
                    strat = resource.usage_strategies["m1_nano"]
                    self.assertEqual(strat.volume, 1)
                if resource.id == "9a9e7c74-2a2f-4a30-bc75-fadcbc5f304a":
                    strat = resource.usage_strategies["m1_micro"]
                    self.assertEqual(strat.volume, 1)
                if resource.id == "0a57e3da-9e85-4690-8ba9-ee7573619ec3":
                    strat = resource.usage_strategies["m1_small"]
                    self.assertEqual(strat.volume, 1)
                if resource.id == "388b3939-8854-4a1b-a133-e738f1ffbb0a":
                    strat = resource.usage_strategies["m1_micro"]
                    self.assertEqual(strat.volume, 1)
                if resource.id == "de35c688-5a82-4ce5-a7e0-36245d2448bc":
                    strat = resource.usage_strategies["m1_tiny"]
                    self.assertEqual(strat.volume, 1)
                if resource.id == "e404920f-cfc8-40ba-bc53-a5c610714bd":
                    strat = resource.usage_strategies["m1_medium"]
                    self.assertEqual(strat.volume, 0)

                if resource.id == "3f7b702e4ca14cd99aebf4c4320e00ec":
                    strat = resource.usage_strategies["storage_size"]
                    self.assertEqual(strat.volume, Decimal('276.1893720000'))

                if (resource.id ==
                        "nova-instance-instance-00000002-fa163ee2d5f6"):
                    strat = resource.usage_strategies["outgoing_megabytes"]
                    self.assertEqual(strat.volume, Decimal('0.0118220000'))
                    strat = resource.usage_strategies["incoming_megabytes"]
                    self.assertEqual(strat.volume, Decimal('0.0097340000'))
                if (resource.id ==
                        "nova-instance-instance-00000001-fa163edf2e3c"):
                    strat = resource.usage_strategies["outgoing_megabytes"]
                    self.assertEqual(strat.volume, Decimal('0.0063060000'))
                    strat = resource.usage_strategies["incoming_megabytes"]
                    self.assertEqual(strat.volume, Decimal('0.0058400000'))
                if (resource.id ==
                        "nova-instance-instance-00000005-fa163ee2fde1"):
                    strat = resource.usage_strategies["outgoing_megabytes"]
                    self.assertEqual(strat.volume, Decimal('0.0134060000'))
                    strat = resource.usage_strategies["incoming_megabytes"]
                    self.assertEqual(strat.volume, Decimal('0.0107950000'))

                if (resource.id ==
                        "e788c617-01e9-405b-823f-803f44fb3483"):
                    strat = resource.usage_strategies["volume_size"]
                    self.assertEqual(strat.volume, Decimal('0.0000450000'))
                if (resource.id ==
                        "6af83f4f-1f4f-40cf-810e-e3262dec718f"):
                    strat = resource.usage_strategies["volume_size"]
                    self.assertEqual(strat.volume, Decimal('0.0000030000'))

                if (resource.id ==
                        "84326068-5ccd-4a32-bcd2-c6c3af84d862"):
                    strat = resource.usage_strategies["floating_ip"]
                    self.assertEqual(strat.volume, 1)
                if (resource.id ==
                        "2155db5c-4c7b-4787-90ff-7b8ded741c75"):
                    strat = resource.usage_strategies["floating_ip"]
                    self.assertEqual(strat.volume, 1)

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

        db.session.add(Tenant(tenant_id="3f7b702e4ca14cd99aebf4c4320e00ec",
                              name="demo"))

        tenants = db.tenants(self.start, self.end,
                             ("3f7b702e4ca14cd99aebf4c4320e00ec",))

        self.assertEqual(len(tenants), 1)
