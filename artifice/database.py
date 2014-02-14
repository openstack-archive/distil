from sqlalchemy import func
from sqlalchemy.sql import exists
from .models.db_models import Tenant as tenant_model
from .models.db_models import UsageEntry, Resource
from .models import billing, Base
import collections

import json
from decimal import Decimal

from sqlalchemy import create_engine
import os


class Database(object):

    def __init__(self, config, session):
        self.session = session
        engine = create_engine(os.environ["DATABASE_URL"])
        Base.metadata.create_all(engine)

    def enter(self, usage, start, end):
        """Creates a new database entry for every usage strategy
           in a resource, for all the resources given"""

        # self.session.begin()
        for element in usage:
            for key in element.usage_strategies:
                strategy = element.usage_strategies[key]
                volume = element.get(strategy['usage'])
                try:
                    service = element.get(strategy['service'])
                except AttributeError:
                    service = strategy['service']
                resource_id = element.get("resource_id")
                tenant_id = element.get("tenant_id")

                #  Have we seen this resource before?
                query = self.session.query(Resource).\
                    filter(Resource.resource_id == element.get("resource_id"))
                if query.count() == 0:
                    el_type = element.type
                    if el_type != 'virtual_machine':
                        info = json.dumps({'type': el_type})
                    else:
                        info = json.dumps({'type': el_type,
                                           'name': element.name})
                    # info should really be a json...
                    # but is just a dict cast to a str for now
                    self.session.add(Resource(resource_id=
                                              element.get("resource_id"),
                                              info=str(info)))

                entry = UsageEntry(service=service, volume=volume,
                                   resource_id=resource_id,
                                   tenant_id=tenant_id,
                                   start=start, end=end
                                   )
                self.session.add(entry)
        self.session.commit()

    def tenants(self, start, end, tenants=None):
        """Returns a list of tenants based on the usage entries
           in the given range.
           start, end: define the range to query
           teants: is a iterable of tenants,
                   if not given will default to whole tenant list."""

        if tenants is None:
            tenants = self.session.query(tenant_model.tenant_id).\
                filter(tenant_model.active)
        elif not isinstance(tenants, collections.Iterable):
            raise AttributeError("tenants is not an iterable")

        if start > end:
            raise AttributeError("End must be a later date than start.")

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
            usage_strat = billing.UsageStrategy(entry.service,
                                                Decimal(entry[3]))

            # does this tenant exist yet?
            if entry.tenant_id not in tenants_dict:
                # build resource:
                info = self.session.query(Resource.info).\
                    filter(Resource.resource_id == entry.resource_id)
                metadata = json.loads(info[0].info)
                resource = billing.Resource(metadata, entry.resource_id)

                # add strat to resource:
                resource.usage_strategies[entry.service] = usage_strat

                # build tenant:
                name = self.session.query(tenant_model.name).\
                    filter(tenant_model.tenant_id == entry.tenant_id)
                tenant = billing.Tenant(name[0].name, entry.tenant_id)
                # add resource to tenant:
                tenant.resources[entry.resource_id] = resource
                # add tenant to dict:
                tenants_dict[entry.tenant_id] = tenant

            # tenant exists, but does the resource?
            elif (entry.resource_id not
                  in tenants_dict[entry.tenant_id].resources):
                # build resource
                info = self.session.query(Resource.info).\
                    filter(Resource.resource_id == entry.resource_id)
                metadata = json.loads(info[0].info)
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
