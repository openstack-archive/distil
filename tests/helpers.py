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

import mock
from distil import models
from datetime import timedelta
import json


def fill_db(session, numb_tenants, numb_resources, now):
    for i in range(numb_tenants):
        session.add(models.Tenant(
            id="tenant_id_" + str(i),
            info="metadata",
            name="tenant_name_" + str(i),
            created=now,
            last_collected=now
        ))
        for ii in range(numb_resources):
            session.add(models.Resource(
                id="resource_id_" + str(ii),
                info=json.dumps({"type": "Resource" + str(ii)}),
                tenant_id="tenant_id_" + str(i),
                created=now
            ))
            session.add(models.UsageEntry(
                service="service" + str(ii),
                volume=5,
                unit='gigabyte',
                resource_id="resource_id_" + str(ii),
                tenant_id="tenant_id_" + str(i),
                start=(now - timedelta(days=20)),
                end=now,
                created=now
            ))
    session.commit()


def create_usage_entries(num_resources, num_services, volume):
    entries = []
    for i in range(num_resources):
        for ii in range(num_services):
            entry = mock.MagicMock()
            entry.volume = volume
            entry.service = "service" + str(ii)
            entry.resource_id = "resource_id_" + str(i)
            entries.append(entry)

    return entries
