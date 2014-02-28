from . import test_interface, helpers
from artifice import database
from artifice import models
from datetime import timedelta


class TestDatabaseModule(test_interface.TestInterface):

    def tearDown(self):
        super(TestDatabaseModule, self).tearDown()

    def test_adding_to_db(self):
        """Tests adding all the data to the database."""

        usage = helpers.get_usage()

        db = database.Database(self.session)
        db.insert_tenant("3f7b702e4ca14cd99aebf4c4320e00ec",
                         "demo", "")

        db.enter(usage.values(), self.start, self.end)

        count = 0
        for val in usage.values():
            for strat in val.usage_strategies:
                count += 1

        self.assertEqual(self.session.query(models.UsageEntry).count(), count)
        self.assertEqual(self.session.query(models.Resource).count(),
                         len(usage.values()))
        self.assertEqual(self.session.query(models.Tenant).count(), 1)

    def test_get_from_db(self):
        """Test to return a list of billable tenant objects,
           with the 'tenants' parameter as None, which should
           default to all tenants in the tenant table (just demo)."""
        numb_services = 32

        helpers.fill_db(self.session, 5, numb_services, self.end)

        db = database.Database(self.session)

        for i in range(5):
            usage = db.usage(self.start, self.start + timedelta(days=60),
                             "tenant_id_" + str(i))
            self.assertEqual(usage.count(), numb_services)
