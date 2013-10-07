import unittest
from . import test_interface
from artifice.interface import Artifice
from artifice import invoice
import os
import glob
import mock
from decimal import *

import csv, yaml

try:
    fn = os.path.abspath(__file__)
    path, f = os.path.split(fn)
except NameError:
    path = os.getcwd()


bad_rates_file = os.path.join( path, "data/csv_bad_rates.csv")
bad_names_file = os.path.join( path, "data/csv_bad_names.csv")

good_names_file = os.path.join( path, "data/csv_names.csv")
good_rates_file = os.path.join( path, "data/csv_rates.csv")

test_interface.config["invoice_object"] = {
    "output_path": "./",
    "output_file": "%(tenant)s-%(start)s-%(end)s.csv",
    "delimiter": ",",
    "row_layout": ["location", "type", "start", "end", "amount", "cost"],
    "rates": {
        "file": good_rates_file,
        "name": good_names_file,
    }
}
test_interface.config["main"]["invoice:object"] = "billing.csv_invoice:Csv"


class TestInvoice(test_interface.TestInterface):


    def tearDown(self):

        super(TestInvoice, self).tearDown()

        [os.unlink(a) for a in glob.glob("./*.csv")]

        # Reset the file paths
        test_interface.config["invoice_object"]["rates"]["file"] = good_rates_file
        test_interface.config["invoice_object"]["rates"]["name"] = good_names_file

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

        # We need to grab the costing info here

        # fh = open(test_interface.config["invoice_object"]["rates"]["file"])
        # rates = {}
        # reader = csv.reader(fh, delimiter = "|")
        # This is not ideal.
        class Reader(invoice.RatesFileMixin, invoice.NamesFileMixin):
            def __init__(self):
                self.config = {
                    "rates": {
                        "file": test_interface.config["invoice_object"]["rates"]["file"],
                        "name": test_interface.config["invoice_object"]["rates"]["name"]
                    }
                }
        # for row in reader:
        #     # The default layout is expected to be:
        #     # location | rate name | rate measurement | rate value
        #     rates[row[1].strip()] = {
        #         "cost": row[3].strip(),
        #         "region": row[0].strip(),
        #         "measures": row[2].strip()
        #     }
        # fh.close()
        r = Reader()

        for uvm, cvm in zip(self.usage.vms, rows):
            print cvm
            self.assertEqual(
                uvm.amount.volume() * r.rate(r.pretty_name(uvm.type)),
                Decimal( cvm[-1] )
            )


    def test_bad_rates_file(self):
        """test raising an exception with a malformed rates file"""
        test_interface.config["invoice_object"]["rates"]["file"] = \
            bad_rates_file
        self.assertRaises(IndexError, self.test_creates_csv )

    def test_missing_rates_file(self):
        """test raising an exception with a missing rates file"""
        test_interface.config["invoice_object"]["rates"]["file"] = \
            "Missing_rates_file"
        self.assertRaises(IOError, self.test_creates_csv )

    def test_missing_names_file(self):
        """test raising an exception with a missing names file"""
        """test raising an exception with a missing rates file"""
        test_interface.config["invoice_object"]["rates"]["name"] = \
            "Missing_rates_file"
        self.assertRaises(IOError, self.test_creates_csv )

    def test_bad_names_file(self):
        """test raising an exception with a malformed names file"""
        pass

    def test_csv_rates_match(self):
        """test rates in output CSV match computed rates"""
        pass

    def test_names_match(self):
        """test names in output CSV match pretty names"""
        pass