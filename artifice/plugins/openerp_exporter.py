import oerplib
from collections import defaultdict
from artifice import invoice

class connection(object):
    def __init__(self, config):
        self.config = config
        self.oerp = oerplib()
        self.sections = []
        self._data = defaultdict(list)
        self.this_section = None

    def create(self):
        pass

    def section(self, title):

        if title not in self.sections:
            self.sections.append(title)
        self.this_section = title

    def add_line(self, text, value):
        self._data[self.this_section].append((text, value))

    def cost(self, datacenter, meter):
        """Returns the cost of a given resource in a given datacenter."""
        return costs[meter][datacenter]


class OpenERP(invoice.Invoice):

    def __init__(self, tenant, config):

        super(OpenERP, self).__init__(tenant)
        # Conn is expected to be a dict with:
        self.conn = connection(self.config)
        self.id = self.conn.create()

    def add_section(self, name):
        self.conn.section(name)

    def add_line(self, item):
        """
        """

        datacenter, name, value = item
        self.conn.section( datacenter )

        cost = self.conn.cost(datacenter, name)

        self.conn.add_line( name, cost * value )

    def commit(self):
        self.conn.bill(self.id)
        return self.id


    def close(self):
        """
        Makes this invoice no longer writable - it's closed and registered as
        a closed invoice in OpenERP; sent out for payment, etc.
        """
        pass

    def cost(self, datacenter, name):
        return self.conn.cost(datacenter, name)