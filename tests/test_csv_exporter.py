from . import test_interface
from tests import helpers
from artifice.plugins import csv_exporter
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

    def make_csv_file(self, csv_config, numb_resources):
        tenant = helpers.build_billable(numb_resources)

        sales_order = csv_exporter.Csv(self.start, self.end,
                                       csv_config)
        sales_order.bill(tenant)
        self.filename = sales_order.filename
        sales_order.close()

    def test_generate_csv(self):
        """Generates a CSV, checks that the
           right number of resources are there,
           and that the dates match."""
        numb_resources = 10

        self.make_csv_file(config, numb_resources)

        with open(self.filename, 'rb') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')

            count = 0
            for row in reader:
                print row
                try:
                    if row[0] == "usage range":
                        self.assertEquals(row[1], str(self.start))
                        self.assertEquals(row[2], str(self.end))
                    elif row[0].startswith("resource_id"):
                        count += 1
                except IndexError:
                    # just and empty row
                    pass

        self.assertEqual(numb_resources, count)

    def test_csv_order_1(self):
        """Generates a CSV, and checks that the order of types is correct."""
        numb_resources = 10

        self.make_csv_file(config, numb_resources)

        with open(self.filename, 'rb') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')

            count = 0
            count2 = 0
            resource = False
            for row in reader:
                print row
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

        config2 = dict(config)
        config2["type_order"] = ["type_1", "type_2", "type_4", "type_5",
                                 "type_6", "type_8", "type_9"]

        self.make_csv_file(config2, numb_resources)

        with open(self.filename, 'rb') as csvfile:
            reader = csv.reader(csvfile, delimiter=',')

            count = 0
            count2 = 0
            resource = False
            for row in reader:
                print row
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
