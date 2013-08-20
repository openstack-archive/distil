import unittest
from . import test_interface
from artifice.interface import Artifice
import os
import glob
import mock

import csv


test_interface.config["invoice_object"] = {
    "output_path": "./",
    "output_file": "%(tenant)s-%(start)s-%(end)s.csv",
    "delimiter": ",",
    "row_layout": ["location", "type", "start", "end", "amount", "cost"]
}
test_interface.config["main"]["invoice:object"] = "billing.csv_invoice:Csv"


class TestInvoice(test_interface.TestInterface):


    def tearDown(self):

        super(TestInvoice, self).tearDown()

        [os.unlink(a) for a in glob.glob("./*.csv")]

    @mock.patch("artifice.models.Session")
    @mock.patch("artifice.interface.keystone")
    @mock.patch("sqlalchemy.create_engine")
    def test_artifice_loads_csv_module(self, sqlmock, keystone, session):
        """Loading and instancing the CSV module works as expected: """

        self.test_save_contents()
        t = self.artifice.tenants[ self.artifice.tenants.keys()[0] ]
        try:
            i = t.invoice(self.start, self.end)
        except ImportError as e:
            self.fail("Couldn't import: %s" % e)
        return i

    def test_adding_to_invoice(self):

        i = self.test_artifice_loads_csv_module()
        i.bill( self.usage.vms )

        self.assertTrue( len(i.lines) > 0 )
        return i

    def test_creates_csv(self):

        i = self.test_adding_to_invoice()
        i.close() # Should save to disk

        self.assertTrue( os.path.exists(i.filename) )

        return i

    def test_csv_matches_data(self):

        i = self.test_creates_csv()
        fh = open(i.filename)

        r = csv.reader(fh)
        rows = [row for row in r] # slurp
        fh.close()

        for uvm, cvm in zip(self.usage.vms, rows):
            self.assertEqual( uvm.amount, cvm[-2] )
