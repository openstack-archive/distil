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
from decimal import Decimal
from datetime import datetime

from oslo_config import cfg
from oslo_log import log as logging
from distil.db import api as db_api
from stevedore import driver

from distil.utils import general
from distil.common import constants

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


def get_costs(project_id, start, end):
    try:
        if start is not None:
            try:
                start = datetime.strptime(start, constants.iso_date)
            except ValueError:
                start = datetime.strptime(start, constants.iso_time)
        else:
            return 400, {"missing parameter": {"start": "start date" +
                                               " in format: y-m-d"}}
        if not end:
            end = datetime.utcnow()
        else:
            try:
                end = datetime.strptime(end, constants.iso_date)
            except ValueError:
                end = datetime.strptime(end, constants.iso_time)
    except ValueError:
            return 400, {
                "errors": ["'end' date given needs to be in format: " +
                           "y-m-d, or y-m-dTH:M:S"]}

    if end <= start:
        return 400, {"errors": ["end date must be greater than start."]}

    valid_project = db_api.project_get(project_id)
    if isinstance(valid_project, tuple):
        return valid_project

    LOG.debug("Calculating rated data for %s in range: %s - %s" %
              (valid_project.id, start, end))

    costs = _calculate_cost(valid_project, start, end)

    return costs


def _calculate_cost(project, start, end):
    """Calculate a rated data dict from the given range."""

    usages = db_api.usage_get(project.id, start, end)

    # Transform the query result into a billable dict.
    project_dict = _build_project_dict(project, usages)
    project_dict = _add_costs_for_project(project_dict)

    # add sales order range:
    project_dict['start'] = str(start)
    project_dict['end'] = str(end)

    return project_dict


def _build_project_dict(project, usages):
    """Builds a dict structure for a given project."""

    project_dict = {'name': project.name, 'project_id': project.id}

    # TODO(flwang): Need to debug why the entry is not an object of UsageEntry
    # but a dict
    all_resource_ids = {entry.get('resource_id') for entry in usages}
    res_list = db_api.resource_get_by_ids(project.id, all_resource_ids)
    project_dict['resources'] = {row.id: json.loads(row.info)
                                 for row in res_list}

    for entry in usages:
        service = {'name': entry.get('service'),
                   'volume': entry.get('volume'),
                   'unit': entry.get('unit')}

        resource = project_dict['resources'][entry.get('resource_id')]
        service_list = resource.setdefault('services', [])
        service_list.append(service)

    return project_dict


def _add_costs_for_project(project):
    rater = driver.DriverManager('distil.rater',
                                 CONF.rater.rater_type,
                                 invoke_on_load=True,
                                 invoke_kwds={}).driver
    """Adds cost values to services using the given rates manager."""

    project_total = 0
    for resource in project['resources'].values():
        resource_total = 0
        for service in resource['services']:
            try:
                rate = rater.rate(service['name'])
            except KeyError:
                # no rate exists for this service
                service['cost'] = "0"
                service['volume'] = "unknown unit conversion"
                service['unit'] = "unknown"
                service['rate'] = "missing rate"
                continue

            volume = general.convert_to(service['volume'],
                                        service['unit'],
                                        rate['unit'])

            # round to 2dp so in dollars.
            cost = round(volume * Decimal(rate['rate']), 2)

            service['cost'] = str(cost)
            service['volume'] = str(volume)
            service['unit'] = rate['unit']
            service['rate'] = str(rate['rate'])

            resource_total += cost
        resource['total_cost'] = str(resource_total)
        project_total += resource_total
    project['total_cost'] = str(project_total)

    return project
