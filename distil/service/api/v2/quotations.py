# Copyright (c) 2017 Catalyst IT Ltd.
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

import copy
from datetime import datetime

from oslo_config import cfg
from oslo_log import log as logging

from distil.common import constants
from distil.common import openstack
from distil.db import api as db_api
from distil.erp import utils as erp_utils

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


def _get_current_region_quotation(project, detailed=False):
    # NOTE(flwang): Use UTC time to avoid timezone conflict
    end = datetime.utcnow()
    start = datetime(end.year, end.month, 1)
    region_name = CONF.keystone_authtoken.region_name

    LOG.info(
        'Get quotations for %s(%s) from %s to %s for current region: %s',
        project.id, project.name, start, end.strftime("%Y-%m-%d"), region_name
    )

    output = {
        'start': str(start),
        'end': str(end.strftime("%Y-%m-%d 00:00:00")),
        'project_id': project.id,
        'project_name': project.name,
    }

    usage = db_api.usage_get(project.id, start, end)
    all_resource_ids = set([entry.get('resource_id') for entry in usage])
    res_list = db_api.resource_get_by_ids(project.id, all_resource_ids)

    erp_driver = erp_utils.load_erp_driver(CONF)
    quotations = erp_driver.get_quotations(
        region_name,
        project.id,
        measurements=usage,
        resources=res_list,
        detailed=detailed
    )

    output['quotations'] = {str(end.date()): quotations}

    return output


def _get_other_regions_quotation_detail(project):
    cur_region = CONF.keystone_authtoken.region_name
    regions = [r.id for r in openstack.get_regions() if r.id != cur_region]
    details_list = []

    for region in regions:
        client = openstack.get_distil_client(region)

        LOG.info(
            'Get quotations for %s(%s) in region: %s',
            project.id, project.name, region
        )

        details = client.quotations.list(
            project_id=project.id, detailed=True
        )['quotations'].values()[0]['details']
        details_list.append(details)

    return details_list


def _merge_detail(a, b, path=None):
    """merges b into a."""
    path = path or []

    for key in b:
        if key not in a:
            a[key] = b[key]
            continue

        if key == 'Object Storage':
            if a[key]['total_cost'] < b[key]['total_cost']:
                a[key] = b[key]
            continue

        if isinstance(a[key], dict) and isinstance(b[key], dict):
            _merge_detail(a[key], b[key], path + [str(key)])
        # Add up 'total_cost'
        elif (isinstance(a[key], (int, float)) and
              isinstance(b[key], (int, float))):
            a[key] = round(float(a[key] + b[key]), 2)
        elif a[key] == b[key]:
            pass
        else:
            raise Exception('Conflict at %s' % '.'.join(path + [str(key)]))

    return a


def _handle_details(details):
    """Convert detail list to a single dict.

    An example return value:
    {
      "Block Storage": {"breakdown": {}, "total_cost": 81.47},
      "Compute": {"breakdown": {}, "total_cost": 129.58},
      "Network": {
        "breakdown": {
          "NZ-POR-1.n1.network": [
            {
              "cost": 3.92,
              "quantity": 239.0,
              "rate": 0.0164,
              "resource_id": "87011816-8702-42f5-a511-4bbc76eecf21",
              "resource_name": "production",
              "unit": "hour"
            }
          ],
          "NZ-WLG-2.n1.network": [
            {
              "cost": 3.92,
              "quantity": 239.0,
              "rate": 0.0164,
              "resource_id": "12345678-8702-42f5-a511-4bbc76eecf21",
              "resource_name": "",
              "unit": "hour"
            }
          ],
          "discount.n1.network": [
            {
              "cost": -7.84,
              "quantity": -478,
              "rate": 0.0164,
              "unit": "hour"
            }
          ]
        },
        "total_cost": 0.0
      },
      "Object Storage": {"breakdown": {}, "total_cost": 78.21}
    }

    1. Only keep object storage usage from one region
    2. Give a discount for the first network and router accross all regions
    """
    service_detail = reduce(_merge_detail, details)

    # Add network/router discount
    network_bd = service_detail['Network']['breakdown']

    network_usage = 0
    network_rate = 0
    router_usage = 0
    router_rate = 0

    # Calculate total network/router hours for all regions
    for name in network_bd:
        if 'n1.network' in name:
            network_rate = network_bd[name][0]['rate']
            network_usage += sum(
                [i['quantity'] for i in network_bd[name]]
            )
        if 'n1.router' in name:
            router_rate = network_bd[name][0]['rate']
            router_usage += sum(
                [i['quantity'] for i in network_bd[name]]
            )

    now = datetime.utcnow()
    start_date = datetime(year=now.year, month=now.month, day=1)
    free_hours = int((now - start_date).total_seconds() / 3600)

    network_free_hours = (network_usage if network_usage < free_hours
                          else free_hours)
    router_free_hours = (router_usage if router_usage < free_hours
                         else free_hours)

    if network_free_hours > 0:
        cost = round(network_rate * network_free_hours, 2)
        network_bd['discount.n1.network'] = [{
            "cost": -cost,
            "quantity": -network_free_hours,
            "rate": network_rate,
            "unit": "hour"
        }]
        service_detail['Network']['total_cost'] = round(
            service_detail['Network']['total_cost'] - cost, 2
        )

    if router_free_hours > 0:
        cost = round(router_rate * router_free_hours, 2)
        network_bd['discount.n1.router'] = [{
            "cost": -cost,
            "quantity": -router_free_hours,
            "rate": router_rate,
            "unit": "hour"
        }]
        service_detail['Network']['total_cost'] = round(
            service_detail['Network']['total_cost'] - cost, 2
        )

    return service_detail


def get_quotations(project_id, detailed=False, all_regions=False):
    """Get quotation for project.

    If all_regions is False, only get current region quotation. Otherwise get
    detailed quotations for all other regions first, and merge to current
    region quotation, the result will only keep Swift usage of one region and
    add network/router discount.
    """
    project = db_api.project_get(project_id)
    ret = _get_current_region_quotation(project, detailed=detailed)

    if not all_regions:
        return ret

    date_key = ret['quotations'].keys()[0]
    other_details = _get_other_regions_quotation_detail(project)

    cur_detail = ret['quotations'][date_key].get('details', {})
    detail_list = [copy.deepcopy(cur_detail)]
    detail_list.extend(other_details)

    new_details = _handle_details(detail_list)
    final_cost = sum([v['total_cost'] for v in new_details.values()])

    if detailed:
        ret['quotations'][date_key]['details'] = new_details
    ret['quotations'][date_key]['total_cost'] = round(
        final_cost, constants.PRICE_DIGITS
    )

    return ret
