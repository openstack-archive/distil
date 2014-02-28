from . import test_interface
from artifice import database
from artifice.models import Tenant
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from artifice.plugins import csv_exporter

Base = declarative_base()


config = {
    "output_file": '%(tenant)s-%(start)s-%(end)s.csv',
    "output_path": "./tests/invoices",
    "rates": {"file":
              "examples/csv_rates.csv"}
}


class TestCSVInvoice(test_interface.TestInterface):

    def tearDown(self):

        super(TestCSVInvoice, self).tearDown()

    def artifice_start_session(self):
        """Loading and instancing the database module works as expected: """
        try:
            db = database.Database(self.session)
        except ImportError as e:
            self.fail("Couldn't import: %s" % e)
        return db

    # def test_generate_csv(self):
    #     """"""
    #     self.test_get_usage()

    #     db = self.artifice_start_session()
    #     db.session.add(Tenant(id="3f7b702e4ca14cd99aebf4c4320e00ec",
    #                           name="demo", info="", created=datetime.now()))

    #     db.enter(self.usage.vms, self.start, self.end)
    #     db.enter(self.usage.objects, self.start, self.end)
    #     db.enter(self.usage.networks, self.start, self.end)
    #     db.enter(self.usage.volumes, self.start, self.end)

    #     tenants = db.tenants(self.start, self.end,
    #                          ("3f7b702e4ca14cd99aebf4c4320e00ec",))
    #     print
    #     for tenant in tenants:
    #         invoice = csv_.Csv(self.start, self.end,
    #                            config)
    #         invoice.bill(tenant)
    #         invoice.close()
