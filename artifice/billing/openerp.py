import oerplib
from artifice import invoice

class connection(object):
    pass

class openerp(invoice.Invoice):

    def save(self):

        """
        Performs the save action against the OpenERP API
        Doesn't do much more than create a thing and
        """
        pass
