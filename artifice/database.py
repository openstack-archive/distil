from sqlalchemy import func
from .models import Resource, UsageEntry, Tenant
import json
from transformers import TransformerValidationError
from datetime import datetime


class Database(object):

    def __init__(self, session):
        self.session = session

    def insert_tenant(self, tenant_id, tenant_name, metadata, timestamp):
        """If a tenant exists does nothing,
           and if it doesn't, creates and inserts it."""
        #  Have we seen this tenant before?
        query = self.session.query(Tenant).\
            filter(Tenant.id == tenant_id)
        if query.count() == 0:
            self.session.add(Tenant(id=tenant_id,
                                    info=metadata,
                                    name=tenant_name,
                                    created=timestamp
                                    ))
            self.session.flush()

    def enter(self, usage, start, end, timestamp):
        """Creates a new database entry for every usage strategy
           in a resource, for all the resources given"""

        for resource in usage:
            resource_id = resource.resource_id
            tenant_id = resource.tenant_id
            try:
                for service, volume in resource.usage().iteritems():
                    #  Have we seen this resource before?
                    query = self.session.query(Resource).\
                        filter(Resource.id == resource_id,
                               Resource.tenant_id == tenant_id)
                    if query.count() == 0:
                        info = json.dumps(resource.info)
                        self.session.add(Resource(id=resource_id,
                                                  info=str(info),
                                                  tenant_id=tenant_id,
                                                  created=timestamp
                                                  ))

                    entry = UsageEntry(service=service,
                                       volume=volume,
                                       resource_id=resource_id,
                                       tenant_id=tenant_id,
                                       start=start,
                                       end=end,
                                       created=timestamp
                                       )
                    self.session.add(entry)
                    self.session.flush()
            except TransformerValidationError:
                # log something related to the resource usage failing
                # transform.
                pass

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
