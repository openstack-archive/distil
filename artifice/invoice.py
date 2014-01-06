# In the real world, costs are expected to be pulled from OpenERP
# As this is kind of an alpha piece of code, costs are pulled from
# RIGHT HERE.

"""
an Invoice interface consists of:
    Creating an Invoice object that relates to a Client
    Fetching costs for a Resource Type in a Datacenter Region
    Adding lines to the Invoice Object, representing a Usage per Time at Cost

"""

from decimal import *

class IntegrityViolation(BaseException): pass

class BillingOverlap(BaseException): pass

class NoSuchType(KeyError): pass

class NoSuchLocation(KeyError): pass

costs = {
    "cpu_util" : { "nova": "1" }
}

class Costs(object):

    def cost(self, location, name):
        """"""
        try:
            locations = costs[name]
        except KeyError:
            raise NoSuchType(name)
        try:
            return locations[location]
        except KeyError:
            raise NoSuchLocation(location)

required = ["add_line", "close"]

def requirements(name, parents, attrs):
    for attr_name in required:
        try:
            assert attr_name in attrs
        except AssertionError:
            raise RuntimeError("%s not in %s" % (attr_name, name))

        try:
            assert callable(attr_name)
        except AssertionError:
            raise RuntimeError("%s is not callable" % (attr_name))
    return type(name, parents, attrs)

class Invoice(object):

    # __metaclass__ = requirements

    def __init__(self, tenant, start, end, config):
        self.tenant = tenant
        self.config = config

    def close(self):
        raise NotImplementedError("Not implemented in base class")

    def pretty_name(self, name):
        return name

    def rate(self, name):
        """Returns the rate for a given internal name
        Expected"""
        return 0

    def bill(self, usage):

        for dc in usage:
            # DC is the name of the DC/region. Or the internal code. W/E.
            # print datacenter
            self.subheading(dc["name"])
            for section in dc["sections"]: # will be vm, network, storage
                self.add_section( section )

                meters = dc["sections"][section]

                for usage in meters:
                    cost = self.cost( dc["name"], meter["name"] )

                    self.add_line( "%s per unit " % cost, usage.volume, cost * usage.volume )
        self.commit() # Writes to OpenERP? Closes the invoice? Something.


    def add_line(self, item):
        raise NotImplementedError("Not implemented in base class")

    def add_section(self, title):
        raise NotImplementedError("Not implemented in base class")

    def total(self):
        raise NotImplementedError("Not implemented in the base class")

import csv
class RatesFileMixin(object):
    # Mixin
    # Adds a rates file loader, expecting various things from the
    # configuration

    def rate(self, name):
        try:
            self.__rates
        except AttributeError:
            self.__rates = {}
        if not self.__rates:
            self.__rates = {}
            try:
                fh = open(self.config["rates"][ "file" ])
                reader = csv.reader(fh, delimiter = "|") # Makes no opinions on the file structure
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
        return self.__rates[name]["cost"] # ignore the regions-ness for now

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
                fh = open(self.config["rates"][ "names" ])
                reader = csv.reader(fh, delimiter="|") # Makes no opinions on the file structure
                for row in reader:
                    # The default layout is expected to be:
                    # internal name | external name
                    self.__names[ row[0].strip() ] = row[1].strip()

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

