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
from datetime import datetime
from decimal import Decimal

from oslo_config import cfg
from oslo_log import log as logging
from oslo_log import helpers as log_helpers

from distil import exceptions
from distil import rater
from distil.common import constants
from distil.db import api as db_api
from distil.common import general

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


@log_helpers.log_method_call
def _validate_project_and_range(project_id, start, end):
    try:
        if start is not None:
            try:
                start = datetime.strptime(start, constants.iso_date)
            except ValueError:
                start = datetime.strptime(start, constants.iso_time)
        else:
            raise exceptions.DateTimeException(
                message=(
                    "Missing parameter:" +
                    "'start' in format: y-m-d or y-m-dTH:M:S"))
        if not end:
            end = datetime.utcnow()
        else:
            try:
                end = datetime.strptime(end, constants.iso_date)
            except ValueError:
                end = datetime.strptime(end, constants.iso_time)
    except ValueError:
            raise exceptions.DateTimeException(
                message=(
                    "Missing parameter: " +
                    "'end' in format: y-m-d or y-m-dTH:M:S"))

    if end <= start:
        raise exceptions.DateTimeException(
            message="End date must be greater than start.")

    if not project_id:
        raise exceptions.NotFoundException("Missing parameter: project_id")
    valid_project = db_api.project_get(project_id)

    return valid_project, start, end


@log_helpers.log_method_call
def get_usage(project_id, start, end):
    cleaned = _validate_project_and_range(project_id, start, end)
    try:
        valid_project, start, end = cleaned
    except ValueError:
        return cleaned

    LOG.debug("Calculating unrated data for %s in range: %s - %s" %
              (valid_project.id, start, end))

    usage = db_api.usage_get(valid_project.id, start, end)

    project_dict = _build_project_dict(valid_project, usage)

    # add range:
    project_dict['start'] = str(start)
    project_dict['end'] = str(end)

    return project_dict


@log_helpers.log_method_call
def get_costs(project_id, start, end):

    valid_project, start, end = _validate_project_and_range(
        project_id, start, end)

    LOG.debug("Calculating rated data for %s in range: %s - %s" %
              (valid_project.id, start, end))

    costs = _calculate_cost(valid_project, start, end)

    return costs


@log_helpers.log_method_call
def _calculate_cost(project, start, end):
    """Calculate a rated data dict from the given range."""

    usage = db_api.usage_get(project.id, start, end)

    # Transform the query result into a billable dict.
    project_dict = _build_project_dict(project, usage)
    project_dict = _add_costs_for_project(project_dict)

    # add sales order range:
    project_dict['start'] = str(start)
    project_dict['end'] = str(end)

    return project_dict


@log_helpers.log_method_call
def _build_project_dict(project, usage):
    """Builds a dict structure for a given project."""

    project_dict = {'name': project.name, 'tenant_id': project.id}

    all_resource_ids = [entry.get('resource_id') for entry in usage]
    res_list = db_api.resource_get_by_ids(project.id, all_resource_ids)
    project_dict['resources'] = {row.id: json.loads(row.info)
                                 for row in res_list}

    for entry in usage:
        service = {'name': entry.get('service'),
                   'volume': entry.get('volume'),
                   'unit': entry.get('unit')}

        resource = project_dict['resources'][entry.get('resource_id')]
        service_list = resource.setdefault('services', [])
        service_list.append(service)

    return project_dict


@log_helpers.log_method_call
def _add_costs_for_project(project):
    """Adds cost values to services using the given rates manager."""

    current_rater = rater.get_rater()

    project_total = 0
    for resource in project['resources'].values():
        resource_total = 0
        for service in resource['services']:
            try:
                rate = current_rater.rate(service['name'])
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
