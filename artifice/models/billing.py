

class Tenant(object):

    def __init__(self, name, tenant_id):
        self.name = name
        self.id = tenant_id
        self.resources = {}


class Resource(object):

    def __init__(self, metadata, resource_id):
        self.metadata = metadata
        self.id = resource_id
        self.usage_strategies = {}


class UsageStrategy(object):

    def __init__(self, service, volume):
        self.service = service
        self.volume = volume
