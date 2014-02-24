# In the real world, costs are expected to be pulled from OpenERP
# As this is kind of an alpha piece of code, costs are pulled from
# RIGHT HERE.

"""
an Invoice interface consists of:
    Creating an Invoice object that relates to a Client
    Fetching costs for a Resource Type in a Datacenter Region
    Adding lines to the Invoice Object, representing a Usage per Time at Cost

"""

from decimal import Decimal
import csv


class Invoice(object):

    # __metaclass__ = requirements

    def __init__(self, start, end, config):
        self.start = start
        self.end = end
        self.config = config

    def close(self):
        raise NotImplementedError("Not implemented in base class")

    def bill(self, tenant):
        self._bill(tenant)

    def _bill(self, tenant):
        raise NotImplementedError("Not implemented in base class")


class RatesFileMixin(object):
    # Mixin
    # Adds a rates file loader, expecting various things from the
    # configuration

    def rate(self, name, region=None):
        try:
            self.__rates
        except AttributeError:
            self.__rates = {}
        if not self.__rates:
            self.__rates = {}
            try:
                fh = open(self.config["rates"]["file"])
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
        return self.__rates[name]["cost"]  # ignore the regions-ness for now


class NamesFileMixin(object):

    # Mixin
    # Adds a name prettifier
    #
    def pretty_name(self, name):
        try:
            self.__names
        except AttributeError:
            self.__names = {}
        if not self.__names:
            self.__names = {}
            try:
                fh = open(self.config["rates"]["names"])
                # Makes no opinions on the file structure
                reader = csv.reader(fh, delimiter="|")
                for row in reader:
                    # The default layout is expected to be:
                    # internal name | external name
                    self.__names[row[0].strip()] = row[1].strip()

                if not self.__names:
                    raise IndexError("Malformed names CSV")
                fh.close()
            except KeyError:
                # couldn't actually find the useful info for rateS?
                print "Couldn't find rates info configuration option!"
                raise
            except IOError:
                print "Couldn't open the file!"
                raise
        return self.__names[name]
