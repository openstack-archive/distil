from . import test_interface
from tests import helpers
from artifice.plugins import csv_exporter
from decimal import Decimal
import csv
import os


config = {
    "type_order": ["type_0", "type_1", "type_2", "type_3", "type_4", "type_5",
                   "type_6", "type_7", "type_8", "type_9"],
    "output_file": '%(tenant)s-%(start)s-%(end)s.csv',
    "output_path": "./tests",
    "rates": {"file":
              "examples/test_rates.csv"}
}


class TestCSVExporter(test_interface.TestInterface):

    def tearDown(self):
        super(TestCSVExporter, self).tearDown()
        os.remove(self.filename)
        self.tenant = None

    def make_csv_file(self, csv_config, numb_resources, volume):
        tenant = helpers.build_billable(numb_resources, volume)
        self.tenant = tenant

        sales_order = csv_exporter.Csv(self.start, self.end,
                                       csv_config)
        sales_order.bill(tenant)
        self.filename = sales_order.filename
        sales_order.close()

    def get_rate(self, service):
        try:
            self.__rates
        except AttributeError:
            self.__rates = {}
        if not self.__rates:
            self.__rates = {}
            try:
                fh = open(config["rates"]["file"])
                # Makes no opinions on the file structure
                reader = csv.reader(fh, delimiter="|")
                for row in reader:
                    # The default layout is expected to be:
                    # location | rate name | rate measurement | rate value
                    self.__rates[row[1].strip()] = {
                        "cost": Decimal(row[3].strip()),
                        "region": row[0].strip(),
                        "measures": row[2].strip()
                    }
                if not self.__rates:
                    raise IndexError("malformed rates CSV!")
                fh.close()
            except KeyError:
                # couldn't actually find the useful info for rateS?
                print "Couldn't find rates info configuration option!"
                raise
            except IndexError:
                raise IndexError("Malformed rates CSV!")
            except IOError:
                print "Couldn't open the file!"
                raise
        return self.__rates[service]["cost"]  # ignore the regions-ness for now

    def test_generate_csv(self):
        """Generates a CSV, checks that:
           -the right number of resources are there,
           -all those are in the billable object too,
           -that the dates match."""
        numb_resources = 10
        volume = 5

        self.make_csv_file(config, numb_resources, volume)

        with open(self.filename, 'rb') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')

            count = 0
            for row in reader:
                try:
                    if row[0] == "usage range":
                        self.assertEquals(row[1], str(self.start))
                        self.assertEquals(row[2], str(self.end))
                    elif row[0].startswith("resource_id"):
                        self.assertTrue(row[0] in self.tenant.resources)
                        count += 1
                except IndexError:
                    # just and empty row
                    pass

        self.assertEqual(numb_resources, count)

    def test_csv_order_1(self):
        """Generates a CSV, and checks that the order of types is correct."""
        numb_resources = 10
        volume = 5

        self.make_csv_file(config, numb_resources, volume)

        with open(self.filename, 'rb') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')

            count = 0
            count2 = 0
            resource = False
            for row in reader:
                try:
                    if resource:
                        if count2 == 1:
                            self.assertEquals(row[0],
                                              config["type_order"][count - 1])
                            count2 = 0
                            resource = False
                        else:
                            count2 += 1
                    elif row[0] == "usage range":
                        self.assertEquals(row[1], str(self.start))
                        self.assertEquals(row[2], str(self.end))
                    elif row[0].startswith("resource_id"):
                        count += 1
                        resource = True
                except IndexError:
                    # just and empty row
                    pass

        self.assertEqual(numb_resources, count)

    def test_csv_order_2(self):
        """Generates a CSV, and checks that the order of types is correct,
           but only for the types given."""
        numb_resources = 10
        volume = 5

        config2 = dict(config)
        config2["type_order"] = ["type_1", "type_2", "type_4", "type_5",
                                 "type_6", "type_8", "type_9"]

        self.make_csv_file(config2, numb_resources, volume)

        with open(self.filename, 'rb') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')

            count = 0
            count2 = 0
            resource = False
            for row in reader:
                try:
                    if resource:
                        if count2 == 1:
                            try:
                                req_type = config2["type_order"][count - 1]
                                self.assertEquals(row[0], req_type)
                            except IndexError:
                                # we've gotten to the end of the required order
                                pass
                            count2 = 0
                            resource = False
                        else:
                            count2 += 1
                    elif row[0] == "usage range":
                        self.assertEquals(row[1], str(self.start))
                        self.assertEquals(row[2], str(self.end))
                    elif row[0].startswith("resource_id"):
                        count += 1
                        resource = True
                except IndexError:
                    # just and empty row
                    pass

        self.assertEqual(numb_resources, count)

    def test_csv_costs_1(self):
        """Generates a CSV, checks that the rates."""
        numb_resources = 2
        volume = 5

        self.make_csv_file(config, numb_resources, volume)

        with open(self.filename, 'rb') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')

            count = 0
            count2 = 0
            resource = None
            for row in reader:
                try:
                    if resource is not None:
                        if count2 == 3:
                            rate = self.get_rate(row[0])
                            usage = self.tenant.resources[resource].\
                                services[row[0]].volume
                            total = rate * Decimal(row[1])

                            self.assertEquals(rate, Decimal(row[2]))
                            self.assertEquals(usage, Decimal(row[1]))
                            self.assertEquals(total, Decimal(row[3]))
                            count2 = 0
                            resource = None
                        else:
                            count2 += 1
                    elif row[0] == "usage range":
                        self.assertEquals(row[1], str(self.start))
                        self.assertEquals(row[2], str(self.end))
                    elif row[0].startswith("resource_id"):
                        count += 1
                        resource = row[0]
                except IndexError:
                    # just and empty row
                    pass

        self.assertEqual(numb_resources, count)
