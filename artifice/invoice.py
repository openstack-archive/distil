# In the real world, costs are expected to be pulled from OpenERP
# As this is kind of an alpha piece of code, costs are pulled from
# RIGHT HERE.

"""
an Invoice interface consists of:
    Creating an Invoice object that relates to a Client
    Fetching costs for a Resource Type in a Datacenter Region
    Adding lines to the Invoice Object, representing a Usage per Time at Cost

"""

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

    def __init__(self, tenant, config):
        self.tenant = tenant
        self.config = config

    def close(self):
        raise NotImplementedError("Not implemented in base class")

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