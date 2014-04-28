from . import test_interface, helpers
from artifice import database
from datetime import timedelta


class TestDatabaseModule(test_interface.TestInterface):

    def test_get_from_db(self):
        """Test to ensure the data in the database matches the data entered."""
        num_resources = 32
        num_tenants = 5

        helpers.fill_db(self.session, num_tenants, num_resources, self.end)

        db = database.Database(self.session)

        for i in range(num_tenants):
            usage = db.usage(self.start, self.start + timedelta(days=60),
                             "tenant_id_" + str(i))
            self.assertEqual(usage.count(), num_resources)
