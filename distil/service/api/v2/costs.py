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

import collections
from decimal import Decimal
from datetime import datetime
from datetime import date
import json
import math

from oslo_config import cfg
from oslo_log import log as logging

from distil.common import constants
from distil.common import general
from distil.db import api as db_api
from distil.erp import utils as erp_utils
from distil import exceptions
from distil.service.api.v2 import products

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

BILLITEM = collections.namedtuple(
    'BillItem',
    ['id', 'resource', 'count', 'cost']
)


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
                "'end' in format: y-m-d or y-m-dTH:M:S")
        )

    if end < start:
        raise exceptions.DateTimeException(
            message="End date must be greater than or equal to start.")

    if not project_id:
        raise exceptions.NotFoundException("Missing parameter: project_id")
    valid_project = db_api.project_get(project_id)

    return valid_project, start, end


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


def _get_service_price(service_name, service_type, prices):
    """Get service price information from price definitions."""
    price = {'service_name': service_name}

    if service_type in prices:
        for s in prices[service_type]:
            if s['resource'] == service_name:
                price.update({'rate': s['price'], 'unit': s['unit']})
                break
    else:
        found = False
        for category, services in prices.items():
            for s in services:
                if s['resource'] == service_name:
                    price.update({'rate': s['price'], 'unit': s['unit']})
                    found = True
                    break

        if not found:
            # Price not found
            price.update({'rate': None, 'unit': None})

    return price


def _build_current_month_cost(project, usage, srv_res_mapping, prices, start,
                              end):
    """Builds a dict structure for a given project for current month.

    The 'breakdown' is a list for mappings from different service type to
    total cost and resource count.

    The 'details' is a mapping from different service type to all related
    resource information.
    """
    output = {
        'billing_date': str(end.date()),
        'total_cost': 0,
        'breakdown': [],
        'details': {}
    }

    price_mapping = {}
    cost_details = collections.defaultdict(list)
    service_cost = collections.OrderedDict()

    all_resource_ids = [entry.get('resource_id') for entry in usage]
    res_list = db_api.resource_get_by_ids(project.id, all_resource_ids)
    resources = {row.id: json.loads(row.info) for row in res_list}

    # Construct resources usage and total cost for each service type.
    for entry in usage:
        service_name = entry.get('service')
        volume = entry.get('volume')
        unit = entry.get('unit')
        res_id = entry.get('resource_id')

        service = {'name': service_name}

        resource_type = resources[res_id]['type']
        service_type = ('Image' if resource_type == 'Image' else
                        srv_res_mapping.get(service_name, resource_type))

        service['resource_id'] = res_id

        if service_name not in price_mapping:
            price_spec = _get_service_price(service_name, service_type, prices)
            price_mapping[service_name] = price_spec
        else:
            price_spec = price_mapping[service_name]

        if price_spec['unit'] is None or price_spec['rate'] is None:
            raise exceptions.NotFoundException(
                'Price not found, service name: %s, service type: %s' %
                (service_name, service_type)
            )

        volume = general.convert_to(volume, unit, price_spec['unit'])
        service['volume'] = str(round(volume, 4))
        cost = (round(volume * Decimal(price_spec['rate']), 2)
                if price_spec['rate'] else 0)
        service['cost'] = str(cost)

        service['unit'] = price_spec['unit'] or "unknown"
        if service_type in ('Image', 'Block Storage', 'Object Storage'):
            service['unit'] = 'gigabyte * hour'

        service['rate'] = str(price_spec['rate']) or "missing rate"

        cost_details[service_type].append(service)

        if service_type in service_cost:
            tmp_count_cost = service_cost[service_type]
            tmp_count_cost = [tmp_count_cost[0] + 1, tmp_count_cost[1] + cost]
            service_cost[service_type] = tmp_count_cost
        else:
            service_cost[service_type] = [1, cost]

    breakdown = []
    total_cost = 0
    free_hours = math.floor((end - start).total_seconds() / 3600)

    for service_type, count_cost in service_cost.iteritems():
        rounded_cost = count_cost[1]

        if service_type in ('Network', 'Router'):
            free_cost = round(
                float(cost_details[service_type][0]['rate']) * free_hours, 2
            )
            free_cost = (rounded_cost if rounded_cost <= free_cost
                         else free_cost)
            rounded_cost = rounded_cost - free_cost

        breakdown.append(
            BILLITEM(
                id=len(breakdown) + 1,
                resource=service_type,
                count=count_cost[0],
                cost=rounded_cost
            )
        )

        total_cost += rounded_cost

    LOG.debug(
        'For current month: total cost: %s, service cost breakdown: %s' %
        (total_cost, breakdown)
    )

    output['total_cost'] = total_cost
    output['breakdown'] = breakdown
    output['details'] = cost_details

    return output


def _calculate_cost(project, start, end):
    """Calculate a rated data dict from the given range."""
    output = {
        'start': str(start),
        'end': str(end),
        'project_name': project.name,
        'project_id': project.id,
        'cost': []
    }

    erp_driver = erp_utils.load_erp_driver(CONF)
    erp_costs = erp_driver.get_costs(start, end, project.id)
    output['cost'].extend(erp_costs)

    # Calculate estimated cost for current month based on current usage in
    # current region.
    if CONF.calculate_current_month:
        today = datetime.today()
        if today.year == end.year and today.month == end.month:
            LOG.debug('Calculate current month cost based on tenant usage.')

            start = datetime(end.year, end.month, 1)
            usage = db_api.usage_get(project.id, start, end)

            region_name = CONF.keystone_authtoken.region_name
            prices = products.get_products([region_name])[region_name]
            srv_res_mapping = erp_driver.get_service_name_mapping(prices)

            output['cost'].append(
                _build_current_month_cost(project, usage, srv_res_mapping,
                                          prices, start, end)
            )

    return output


def get_costs(project_id, start, end):
    valid_project, start, end = _validate_project_and_range(
        project_id, start, end)

    LOG.info("Get cost for %s in range: %s - %s" %
             (valid_project.id, start, end))

    costs = _calculate_cost(valid_project, start, end)

    return costs
