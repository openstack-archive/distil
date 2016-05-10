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

import datetime

from oslo_config import cfg
from oslo_log import log as logging
from distil.db import api as db_api
from stevedore import driver

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


def get_costs(tenant_id, start, end):
    try:
        if start is not None:
            try:
                start = datetime.strptime(start, iso_date)
            except ValueError:
                start = datetime.strptime(start, iso_time)
        else:
            return 400, {"missing parameter": {"start": "start date" +
                                               " in format: y-m-d"}}
        if not end:
            end = datetime.utcnow()
        else:
            try:
                end = datetime.strptime(end, iso_date)
            except ValueError:
                end = datetime.strptime(end, iso_time)
    except ValueError:
            return 400, {
                "errors": ["'end' date given needs to be in format: " +
                           "y-m-d, or y-m-dTH:M:S"]}

    if end <= start:
        return 400, {"errors": ["end date must be greater than start."]}

    valid_tenant = validate_tenant_id(tenant_id, session)
    if isinstance(valid_tenant, tuple):
        return valid_tenant

    if memcache is not None:
        key = make_key("rated_usage", valid_tenant.id, start, end)

        data = memcache.get(key)
        if data is not None:
            log.info("Returning memcache rated data for %s in range: %s - %s" %
                     (valid_tenant.id, start, end))
            return 200, data

    log.info("Calculating rated data for %s in range: %s - %s" %
             (valid_tenant.id, start, end))

    costs = _calculate_cost(valid_tenant, start, end)

    return costs


def _calculate_cost(tenant, start, end):
    """Calculate a rated data dict from the given range."""

    rater = driver.DriverManager('distil.rater',
                                 CONF.rater.rater_type,
                                 invoke_on_load=True,
                                 invoke_kwds={}).driver

    usage = db_api.usage_get(tenant.id, start, end,)

    # Transform the query result into a billable dict.
    tenant_dict = _build_tenant_dict(tenant, usage)
    tenant_dict = _add_costs_for_tenant(tenant_dict, rater)

    # add sales order range:
    tenant_dict['start'] = str(start)
    tenant_dict['end'] = str(end)

    return tenant_dict


def _build_tenant_dict(tenant, entries):
    """Builds a dict structure for a given tenant."""
    tenant_dict = {'name': tenant.name, 'tenant_id': tenant.id}

    all_resource_ids = {entry.resource_id for entry in entries}
    res_list = db_api.resource_get_by_ids(all_resource_ids)
    tenant_dict['resources'] = {row.id: json.loads(row.info)
                                for row in res_list}

    for entry in entries:
        service = {'name': entry.service, 'volume': entry.volume,
                'unit': entry.unit}

        resource = tenant_dict['resources'][entry.resource_id]
        service_list = resource.setdefault('services', [])
        service_list.append(service)

    return tenant_dict


def _add_costs_for_tenant(tenant, rater):
    """Adds cost values to services using the given rates manager."""
    tenant_total = 0
    for resource in tenant['resources'].values():
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

            volume = convert_to(service['volume'],
                                service['unit'],
                                rate['unit'])

            # round to 2dp so in dollars.
            cost = round(volume * rate['rate'], 2)

            service['cost'] = str(cost)
            service['volume'] = str(volume)
            service['unit'] = rate['unit']
            service['rate'] = str(rate['rate'])

            resource_total += cost
        resource['total_cost'] = str(resource_total)
        tenant_total += resource_total
    tenant['total_cost'] = str(tenant_total)

    return tenant
