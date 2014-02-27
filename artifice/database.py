from sqlalchemy import func
from .models import Resource, UsageEntry, Tenant
import json
from datetime import datetime


class Database(object):

    def __init__(self, session):
        self.session = session
        # engine = create_engine(os.environ["DATABASE_URL"])
        # Base.metadata.create_all(engine)

    def insert_tenant(self, tenant_id, tenant_name, metadata):
        """Checks if a tenant exists does nothing,
           and if it doesn't, creates and inserts it."""
        #  Have we seen this tenant before?
        query = self.session.query(Tenant).\
            filter(Tenant.id == tenant_id)
        if query.count() == 0:
            self.session.add(Tenant(id=tenant_id,
                                    info=metadata,
                                    name=tenant_name,
                                    created=datetime.now()
                                    ))
            self.session.flush()

    def enter(self, usage, start, end):
        """Creates a new database entry for every usage strategy
           in a resource, for all the resources given"""

        # Seems to expect somethig else

        for resource in usage:
            # This is where possibly injectable strategies can happen
            for key in resource.usage_strategies:
                strategy = resource.usage_strategies[key]
                volume = resource.get(strategy['usage'])
                try:
                    service = resource.get(strategy['service'])
                except AttributeError:
                    service = strategy['service']
                resource_id = resource.get("resource_id")
                tenant_id = resource.get("tenant_id")

                #  Have we seen this resource before?
                query = self.session.query(Resource).\
                    filter(Resource.id == resource_id,
                           Resource.tenant_id == tenant_id)
                if query.count() == 0:
                    info = json.dumps(resource.info)
                    self.session.add(Resource(id=resource_id,
                                              info=str(info),
                                              tenant_id=tenant_id,
                                              created=datetime.now()
                                              ))

                entry = UsageEntry(service=service,
                                   volume=volume,
                                   resource_id=resource_id,
                                   tenant_id=tenant_id,
                                   start=start,
                                   end=end,
                                   created=datetime.now()
                                   )
                self.session.add(entry)
                self.session.flush()

    def usage(self, start, end, tenant_id):
        """Returns a query of usage entries for a given tenant,
           in the given range.
           start, end: define the range to query
           tenant: a tenant entry (tenant_id for now)"""

        if start > end:
            raise AttributeError("End must be a later date than start.")

        # build a query set in the format:
        # tenant_id  | resource_id | service | sum(volume)
        query = self.session.query(UsageEntry.tenant_id,
                                   UsageEntry.resource_id,
                                   UsageEntry.service,
                                   func.sum(UsageEntry.volume).label("volume")).\
            filter(UsageEntry.start >= start, UsageEntry.end <= end).\
            filter(UsageEntry.tenant_id == tenant_id).\
            group_by(UsageEntry.tenant_id, UsageEntry.resource_id,
                     UsageEntry.service)

        return query
