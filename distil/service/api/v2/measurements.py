# Copyright (c) 2016 Catalyst IT Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json

from oslo_log import log as logging

from distil.common import general
from distil.db import api as db_api

LOG = logging.getLogger(__name__)


def _build_project_dict(project, usage):
    """Builds a dict structure for a given project."""

    project_dict = {'project_name': project.name, 'project_id': project.id}

    all_resource_ids = [entry.get('resource_id') for entry in usage]
    res_list = db_api.resource_get_by_ids(project.id, all_resource_ids)
    project_dict['resources'] = {row.id: json.loads(row.info)
                                 for row in res_list}

    for entry in usage:
        service = {'name': entry.get('service'),
                   'volume': str(entry.get('volume')),
                   'unit': entry.get('unit')}

        resource = project_dict['resources'][entry.get('resource_id')]
        service_list = resource.setdefault('services', [])
        service_list.append(service)

    return project_dict


def get_measurements(project_id, start, end):
    valid_project, start, end = general.convert_project_and_range(
        project_id, start, end)

    LOG.debug("Get measurements for %s in range: %s - %s" %
              (valid_project.id, start, end))

    usage = db_api.usage_get(valid_project.id, start, end)

    project_dict = _build_project_dict(valid_project, usage)

    # add range:
    project_dict['start'] = str(start)
    project_dict['end'] = str(end)

    return project_dict
