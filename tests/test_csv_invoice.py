from . import test_interface
from artifice import database
from artifice.models.db_models import Tenant
from sqlalchemy.ext.declarative import declarative_base

from artifice.billing import csv_invoice

Base = declarative_base()


config = {
    "output_file": '%(tenant)s-%(start)s-%(end)s.csv',
    "output_path": "./invoices",
    "rates": {"file":
              "/home/adriant/Projects/openstack-artifice/examples/csv_rates.csv"}
}


class TestCSVInvoice(test_interface.TestInterface):

    def tearDown(self):

        super(TestCSVInvoice, self).tearDown()

    def artifice_start_session(self):
        """Loading and instancing the database module works as expected: """
        try:
            db = database.Database(None, self.session)
        except ImportError as e:
            self.fail("Couldn't import: %s" % e)
        return db

    def test_generate_csv(self):
        """"""
        self.test_get_usage()

        db = self.artifice_start_session()
        db.enter(self.usage.vms, self.start, self.end)
        db.enter(self.usage.objects, self.start, self.end)
        db.enter(self.usage.networks, self.start, self.end)
        db.enter(self.usage.volumes, self.start, self.end)

        db.session.add(Tenant(tenant_id="3f7b702e4ca14cd99aebf4c4320e00ec",
                              name="demo"))

        tenants = db.tenants(self.start, self.end,
                             ("3f7b702e4ca14cd99aebf4c4320e00ec",))
        print
        for tenant in tenants:
            invoice = csv_invoice.Csv(tenant, self.start, self.end,
                                      config)
            invoice.bill()
            invoice.close()
