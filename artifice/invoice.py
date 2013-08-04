# In the real world, costs are expected to be pulled from OpenERP
# As this is kind of an alpha piece of code, costs are pulled from
# RIGHT HERE.

"""
an Invoice interface consists of:
    Creating an Invoice object that relates to a Client
    Fetching costs for a Resource Type in a Datacenter Region
    Adding lines to the Invoice Object, representing a Usage per Time at Cost

"""

costs = {
    "cpu_util" : { "local": "1"}
}

class Invoice(object):

    def __init__(self, tenant):
        self.tenant = tenant

    def bill(self, usage):
        """
        Expects a list of dicts of datacenters
        Each DC is expected to have a list of Types: VM, Network, Storage
        Each Type is expected have to a list of Meters
        Each Meter is expected to have a Usage method that takes our start
        and end values.
        Each Meter will be entered as a line on the Invoice.
        """

        for dc in usage:
            # DC is the name of the DC/region. Or the internal code. W/E.
            # print datacenter
            self.subheading(dc["name"])
            for section in dc["sections"]: # will be vm, network, storage
                self.subheading( section )

                meters = dc["sections"][section]

                for usage in meters:
                    cost = self.cost( dc["name"], meter["name"] )

                    self.line( "%s per unit " % cost, usage.volume, cost * usage.volume )
        self.commit() # Writes to OpenERP? Closes the invoice? Something.

    def commit(self):
        pass

    def close(self):
        """
        Makes this invoice no longer writable - it's closed and registered as
        a closed invoice in OpenERP; sent out for payment, etc.
        """
        pass

    def cost(self, datacenter, meter):
        """Returns the cost of a given resource in a given datacenter."""
        return costs[meter][datacenter]
