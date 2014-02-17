

class Tenant(object):
    """Billable object representing a tenant,
       and all the resources inside it."""

    def __init__(self, name, tenant_id):
        self.name = name
        self.id = tenant_id
        self.resources = {}


class Resource(object):
    """"""

    def __init__(self, metadata, resource_id):
        self.metadata = metadata
        self.id = resource_id
        self.services = {}


class Service(object):

    def __init__(self, name, volume):
        self.name = name
        self.volume = volume
