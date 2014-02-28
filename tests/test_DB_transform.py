from . import test_interface, helpers
from artifice import database
from artifice import models
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class TestDatabaseModels(test_interface.TestInterface):

    def tearDown(self):

        super(TestDatabaseModels, self).tearDown()

    def artifice_start_session(self):
        """Loading and instancing the database module works as expected: """
        try:
            db = database.Database(self.session)
        except ImportError as e:
            self.fail("Couldn't import: %s" % e)
        return db

    def test_adding_to_db(self):
        """Tests adding all the data to the database."""

        usage = helpers.get_usage()

        db = self.artifice_start_session()
        db.insert_tenant("3f7b702e4ca14cd99aebf4c4320e00ec",
                         "demo", "")

        db.enter(usage.values(), self.start, self.end)

        self.assertEqual(self.session.query(models.UsageEntry).count(), 17)
        self.assertEqual(self.session.query(models.Resource).count(),
                         len(usage.values()))
        self.assertEqual(self.session.query(models.Tenant).count(), 1)

    def test_get_from_db_1(self):
        """Test to return a list of billable tenant objects,
           with the 'tenants' parameter as None, which should
           default to all tenants in the tenant table (just demo)."""
        usage = helpers.get_usage()

        db = self.artifice_start_session()
        db.insert_tenant("3f7b702e4ca14cd99aebf4c4320e00ec",
                         "demo", "")

        db.enter(usage.vms, self.start, self.end)
        db.enter(usage.objects, self.start, self.end)
        db.enter(usage.networks, self.start, self.end)
        db.enter(usage.volumes, self.start, self.end)
        db.enter(usage.ips, self.start, self.end)


    # def test_get_from_db_2(self):
    #     """Test to return a list of billable tenant objects,
    #        with the 'tenants' parameter given a tuple with the
    #        resource_id for the demo tenant."""
    #     self.test_get_usage()

    #     db = self.test_artifice_start_session()
    #     db.session.add(Tenant(id="3f7b702e4ca14cd99aebf4c4320e00ec",
    #                           name="demo", info="", created=datetime.now()))

    #     db.enter(usage.vms, self.start, self.end)
    #     db.enter(usage.objects, self.start, self.end)
    #     db.enter(usage.networks, self.start, self.end)
    #     db.enter(usage.volumes, self.start, self.end)

    #     tenants = db.tenants(self.start, self.end,
    #                          ("3f7b702e4ca14cd99aebf4c4320e00ec",))

    #     self.assertEqual(len(tenants), 1)
