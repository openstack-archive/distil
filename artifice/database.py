from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Text, DateTime, Float, func
from .models.tenants import Tenant as tenant_model
from .models import billing
import collections
Base = declarative_base()


class UsageEntry(Base):
    __tablename__ = 'usage'
    service = Column(Text, primary_key=True)
    volume = Column(Float)
    resource_id = Column(Text, primary_key=True)
    tenant_id = Column(Text, primary_key=True)
    start = Column(DateTime)
    end = Column(DateTime, primary_key=True)
    # metadata = Column(Text)


class SalesOrder(Base):
    __tablename__ = 'sales_orders'
    tenant_id = Column(Text, primary_key=True)
    start = Column(DateTime)
    end = Column(DateTime, primary_key=True)


class Database(object):

    def __init__(self, config, session):
        self.session = session
        pass

    def enter(self, usage, start, end):
        """Creates a new database entry for every usage strategy
           in a resource, for all the resources given"""

        # self.session.begin()
        for element in usage:
            print element
            for key in element.usage_strategies:
                strategy = element.usage_strategies[key]
                volume = float(element.get(strategy['usage']))
                try:
                    service = element.get(strategy['service'])
                except AttributeError:
                    service = strategy['service']
                resource_id = element.get("resource_id")
                tenant_id = element.get("tenant_id")

                # el_type = element.type
                # if el_type != 'virtual_machine':
                #     metadata = {'type': el_type}
                # else:
                #     metadata = {'type': el_type, 'name': element.name,
                #                 'region': element.region}
                # # metadata should really be a json...
                # # but is just a dict cast to a str for now

                entry = UsageEntry(service=service, volume=volume,
                                   resource_id=resource_id,
                                   tenant_id=tenant_id,
                                   start=start, end=end
                                   )
                self.session.add(entry)
        self.session.commit()

    def tenants(self, start, end, tenants=None):
        """Returns a list of tenants based on the usage entries
           in the given range."""

        if tenants is None:
            tenants = self.session.query(tenant_model)
        elif not isinstance(tenants, collections.Iterable):
            raise AttributeError("tenants is not an iterable")

        # build a query set in the format:
        # tenant_id  | resource_id | service | sum(volume)
        query = self.session.query(UsageEntry.tenant_id,
                                   UsageEntry.resource_id,
                                   UsageEntry.service,
                                   func.sum(UsageEntry.volume)).\
            filter(UsageEntry.start >= start, UsageEntry.end <= end).\
            filter(UsageEntry.tenant_id.in_(tenants)).\
            group_by(UsageEntry.tenant_id, UsageEntry.resource_id,
                     UsageEntry.service)

        tenants_dict = {}
        for entry in query:
            # since there is no field for volume after the sum, we must
            # access the entry by index
            usage_strat = billing.UsageStrategy(entry.service, entry[3])

            # does this tenant exist yet?
            if entry.tenant_id not in tenants_dict:
                # build resource:
                # metadata = session.query(ResourceMetadata.metadata).\
                #   filter(ResourceMetadata.resource_id=entry.resource_id)
                # temp variable to stop syntax highlighting :P
                metadata = {}
                resource = billing.Resource(metadata, entry.resource_id)

                # add strat to resource:
                resource.usage_strategies[entry.service] = usage_strat

                # build tenant:
                # name = self.session.query(tenant_model.name).\
                #     filter(tenant_model.tenant_id == entry.tenant_id)
                name = "no tenant DB yet"
                tenant = billing.Tenant(name, entry.tenant_id)
                # add resource to tenant:
                tenant.resources[entry.resource_id] = resource
                # add tenant to dict:
                tenants_dict[entry.tenant_id] = tenant

            # tenant exists, but does the resource?
            elif entry.resource_id not in tenants_dict[entry.tenant_id].resources:
                # build resource
                metadata = {}
                resource = billing.Resource(metadata, entry.resource_id)

                # add strat to resource:
                resource.usage_strategies[entry.service] = usage_strat

                tenant = tenants_dict[entry.tenant_id]
                tenant.resources[entry.resource_id] = resource

            # both seem to exist!
            else:
                resource = tenant.resources[entry.resource_id]
                # add strat to resource:
                resource.usage_strategies[entry.service] = usage_strat

        return tenants_dict.values()
