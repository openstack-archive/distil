# Copyright (C) 2014 Catalyst IT Ltd
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from sqlalchemy import func
from .models import Resource, UsageEntry, Tenant, SalesOrder, _Last_Run
from distil.constants import dawn_of_time
from datetime import timedelta
import json
import config
import logging as log


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
            last_run = self.session.query(_Last_Run)
            if last_run.count() == 0:
                start = dawn_of_time
            else:
                # start equals the last run, minus an hour
                # to ensure no data is missed
                start = last_run[0].last_run - timedelta(hours=1)
            tenant = Tenant(id=tenant_id,
                            info=metadata,
                            name=tenant_name,
                            created=timestamp,
                            last_collected=start
                            )
            self.session.add(tenant)
            self.session.flush()           # can't assume deferred constraints.
            return tenant
        else:
            return query[0]

    def insert_resource(self, tenant_id, resource_id, resource_type,
                        timestamp, entry, transform_info):
        """If a given resource does not exist, creates it,
           otherwise merges the metadata with the new entry."""
        md_def = config.collection['metadata_def'].get(resource_type, {})

        query = self.session.query(Resource).\
            filter(Resource.id == resource_id,
                   Resource.tenant_id == tenant_id)
        if query.count() == 0:
            info = self.merge_resource_metadata({'type': resource_type},
                                                entry, transform_info, md_def)
            self.session.add(Resource(
                id=resource_id,
                info=json.dumps(info),
                tenant_id=tenant_id,
                created=timestamp))
            self.session.flush()           # can't assume deferred constraints.
        else:
            md_dict = json.loads(query[0].info)
            md_dict = self.merge_resource_metadata(md_dict, entry,
                                                   transform_info, md_def)
            query[0].info = json.dumps(md_dict)

    def insert_usage(self, tenant_id, resource_id, entries, unit,
                     start, end, timestamp):
        """Inserts all given entries into the database."""
        for service, volume in entries.items():
            entry = UsageEntry(
                service=service,
                volume=volume,
                unit=unit,
                resource_id=resource_id,
                tenant_id=tenant_id,
                start=start,
                end=end,
                created=timestamp)
            self.session.add(entry)
            log.debug(entry)

    def usage(self, start, end, tenant_id):
        """Returns a query of usage entries for a given tenant,
           in the given range.
           start, end: define the range to query
           tenant: a tenant entry (tenant_id for now)"""

        # build a query set in the format:
        # tenant_id  | resource_id | service | unit | sum(volume)
        query = self.session.query(UsageEntry.tenant_id,
                                   UsageEntry.resource_id,
                                   UsageEntry.service,
                                   UsageEntry.unit,
                                   func.sum(UsageEntry.volume).label("volume")).\
            filter(UsageEntry.start >= start, UsageEntry.end <= end).\
            filter(UsageEntry.tenant_id == tenant_id).\
            group_by(UsageEntry.tenant_id, UsageEntry.resource_id,
                     UsageEntry.service, UsageEntry.unit)

        return query

    def get_resource_metadata(self, resource_id):
        """Gets the metadata for a resource and loads it into a dict."""
        info = self.session.query(Resource.info).\
            filter(Resource.id == resource_id)
        return json.loads(info[0].info)

    def get_sales_orders(self, tenant_id, start, end):
        """Returns a query with all sales orders
           for a tenant in the given range."""
        query = self.session.query(SalesOrder).\
            filter(SalesOrder.start <= end, SalesOrder.end >= start).\
            filter(SalesOrder.tenant_id == tenant_id)
        return query

    def merge_resource_metadata(self, md_dict, entry, transform_info, md_def):
        """Strips metadata from the entry as defined in the config,
           and merges it with the given metadata dict."""
        for field, parameters in md_def.iteritems():
            for i, source in enumerate(parameters['sources']):
                try:
                    value = entry['resource_metadata'][source]
                    if transform_info and 'template' in parameters:
                        md_dict[field] = parameters['template'] % value
                        break
                    else:
                        md_dict[field] = value
                        break
                except KeyError:
                    # Just means we haven't found the right value yet.
                    # Or value isn't present.
                    pass

        return md_dict
