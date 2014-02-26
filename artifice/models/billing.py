
from . import Tenant as TenantModel
from . import Resource as ResourceModel
import json


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


def build_billable(entries, session):
    """Builds a Tenant object and its resources.
       Assumes that all entries are for the same tenant."""
    tenant = None
    for entry in entries:
        service = Service(entry.service, entry.volume)

        # does this tenant exist yet?
        if not tenant:
            # build resource:
            info = session.query(ResourceModel.info).\
                filter(ResourceModel.resource_id == entry.resource_id)
            metadata = json.loads(info[0].info)
            resource = Resource(metadata, entry.resource_id)

            # add strat to resource:
            resource.services[entry.service] = service

            # build tenant:
            name = session.query(TenantModel.name).\
                filter(TenantModel.tenant_id == entry.tenant_id)
            tenant = Tenant(name[0].name, entry.tenant_id)
            # add resource to tenant:
            tenant.resources[entry.resource_id] = resource

        # tenant exists, but does the resource?
        elif (entry.resource_id not in tenant.resources):
            # build resource
            info = session.query(ResourceModel.info).\
                filter(ResourceModel.resource_id == entry.resource_id)
            metadata = json.loads(info[0].info)
            resource = Resource(metadata, entry.resource_id)

            # add strat to resource:
            resource.services[entry.service] = service

            # add resource to tenant
            tenant.resources[entry.resource_id] = resource

        # both seem to exist!
        else:
            resource = tenant.resources[entry.resource_id]
            # add strat to resource:
            resource.services[entry.service] = service

    return tenant
