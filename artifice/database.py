from sqlalchemy import func
from .models import Resource, UsageEntry
import json


class Database(object):

    def __init__(self, config, session):
        self.session = session
        # engine = create_engine(os.environ["DATABASE_URL"])
        # Base.metadata.create_all(engine)

    def enter(self, usage, start, end):
        """Creates a new database entry for every usage strategy
           in a resource, for all the resources given"""

        # self.session.begin()
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
                    filter(Resource.resource_id == resource.get("resource_id"))
                if query.count() == 0:
                    info = json.dumps(resource.info)
                    self.session.add(Resource(resource_id=
                                              resource.get("resource_id"),
                                              info=str(info),
                                              tenant_id=tenant_id
                                              ))

                entry = UsageEntry(service=service,
                                   volume=volume,
                                   resource_id=resource_id,
                                   tenant_id=tenant_id,
                                   start=start,
                                   end=end
                                   )
                self.session.add(entry)
        self.session.commit()

    def usage(self, start, end, tenant):
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
            filter(UsageEntry.tenant_id == tenant).\
            group_by(UsageEntry.tenant_id, UsageEntry.resource_id,
                     UsageEntry.service)

        return query
