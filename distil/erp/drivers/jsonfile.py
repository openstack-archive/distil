# Copyright 2019 Catalyst IT Ltd
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
import copy
from datetime import datetime
from datetime import timedelta
import decimal
import os
import json
import itertools

from oslo_config import cfg
from oslo_log import log

from distil.common import cache
from distil.common import constants
from distil import exceptions
from distil.common import general
from distil.db import api as db_api
from distil.erp import driver

LOG = log.getLogger(__name__)
CONF = cfg.CONF


class JsonFileDriver(driver.BaseDriver):
    """Json driver
    """
    conf = None

    def __init__(self, conf):
        self.conf = conf

    def _load_products(self):
        try:
            with open(self.conf['jsonfile']['products_file_path']) as fh:
                products = json.load(fh)
                return products
        except Exception as e:
            LOG.critical('Failed to load rates json file: `%s`' % e)
            raise e

    def is_healthy(self):
        """Check if the ERP back end is healthy or not

        :returns True if the ERP is healthy, otherwise False
        """
        try:
            p = self._load_products()
            return p is not None
        except Exception as e:
            LOG.error(e)
            return False

    def get_products(self, regions=[]):
        """List products based on given regions

        :param regions: List of regions to get projects
        :returns Dict of products based on the given regions
        """
        # TODO(flwang): Apply regions
        products = self._load_products()
        if regions:
            region_products = {}
            for r in regions:
                if r in products:
                    region_products[r] = products[r]
            return region_products
        return products

    def create_product(self, product):
        """Create product in ERP backend.

        :param product: info used to create product
        """
        raise NotImplementedError()

    def get_credits(self, project_id, expiry_date):
        """Get project credits

        :param project_id: Project ID
        :param expiry_date: Any credit which expires after this date can be
                            listed
        :returns list of credits current project can get
        """
        raise NotImplementedError()

    def create_credit(self, project, credit):
        """Create credit for a given project

        :param project: project
        """
        raise NotImplementedError()

    def _get_invoice_time_ranges(self, start, end):
        previous_months = []

        indicator = end
        while start <= indicator - timedelta(seconds=1):
            end_inv = indicator.replace(
                day=1, hour=0, minute=0, second=0, microsecond=0)

            last_month = indicator.month - 1
            if last_month:
                indicator = indicator.replace(
                    month=last_month, day=1, hour=0, minute=0, second=0,
                    microsecond=0)
            else:
                last_year = indicator.year - 1
                indicator = indicator.replace(
                    year=last_year, month=12, day=1, hour=0, minute=0,
                    second=0, microsecond=0)

            bill_date = end_inv - timedelta(seconds=1)

            previous_months.append((
                indicator,
                end_inv,
                bill_date.strftime('%Y-%m-%d')
            ))

        return previous_months

    def get_invoices(self, start, end, project_id, detailed=False):
        """Get history invoices from ERP service given a time range.

        This will only get the history for the current given region.

        :param start: Start time, a datetime object.
        :param end: End time, a datetime object.
        :param project_id: project ID.
        :param detailed: If get detailed information or not.
        :return: The history invoices information for each month.
        """
        region_name = CONF.keystone_authtoken.region_name

        previous_months = self._get_invoice_time_ranges(start, end)

        invoices = {}
        for start_inv, end_inv, bill_date_str in previous_months:

            usage = db_api.usage_get(project_id, start_inv, end_inv)
            all_resource_ids = set(
                [entry.get('resource_id') for entry in usage])
            res_list = db_api.resource_get_by_ids(project_id, all_resource_ids)
            quotation = self.get_quotations(
                region_name,
                project_id,
                measurements=usage,
                resources=res_list,
                detailed=detailed
            )
            quotation['status'] = 'paid'
            invoices[bill_date_str] = quotation
        return invoices

    @cache.memoize
    def _get_service_mapping(self, products):
        """Gets mapping from service name to service type.

        :param products: Product dict in a region returned from odoo.
        """
        srv_mapping = {}

        for category, p_list in products.items():
            for p in p_list:
                srv_mapping[p['name']] = category.title()

        return srv_mapping

    @cache.memoize
    def _get_service_price(self, service_name, service_type, products):
        """Get service price information from price definitions."""
        price = {'service_name': service_name}

        if service_type in products:
            for s in products[service_type]:
                if s['name'] == service_name:
                    price.update({'rate': s['rate'], 'unit': s['unit']})
                    break
        else:
            found = False
            for category, services in products.items():
                for s in services:
                    if s['name'] == service_name:
                        price.update({'rate': s['rate'], 'unit': s['unit']})
                        found = True
                        break

            if not found:
                raise exceptions.NotFoundException(
                    'Price not found, service name: %s, service type: %s' %
                    (service_name, service_type)
                )

        return price

    def _get_entry_info(self, entry, resources_info, service_mapping):
        service_name = entry.get('service')
        volume = entry.get('volume')
        unit = entry.get('unit')
        res_id = entry.get('resource_id')
        resource = resources_info.get(res_id, {})
        # resource_type is the type defined in meter_mappings.yml.
        resource_type = resource.get('type')
        service_type = service_mapping.get(service_name, resource_type)

        return (service_name, service_type, volume, unit, resource,
                resource_type)

    def get_quotations(self, region, project_id, measurements=[], resources=[],
                       detailed=False):
        """Get current month quotation.

        Return value is in the following format:
        {
          '<current_date>': {
            'total_cost': 100,
            'details': {
                'Compute': {
                    'total_cost': xxx,
                    'breakdown': {}
                }
            }
          }
        }

        :param region: Region name.
        :param project_id: Project ID.
        :param measurements: Current month usage collection.
        :param resources: List of resources.
        :param detailed: If get detailed information or not.
        :return: Current month quotation.
        """
        total_cost = 0
        price_mapping = {}
        cost_details = {}

        resources_info = {}
        for row in resources:
            info = json.loads(row.info)
            info.update({'id': row.id})
            resources_info[row.id] = info

        # NOTE(flwang): For most of the cases of Distil API, the request comes
        # from billing panel. Billing panel sends 1 API call for /invoices and
        # several API calls for /quotations against different regions. So it's
        # not efficient to specify the region for get_products method because
        # it won't help cache the products based on the parameters.
        products = self.get_products()[region]
        service_mapping = self._get_service_mapping(products)

        for entry in measurements:
            (service_name, service_type, volume, unit, resource,
             resource_type) = self._get_entry_info(entry, resources_info,
                                                   service_mapping)
            res_id = resource['id']

            if service_type not in cost_details:
                cost_details[service_type] = {
                    'total_cost': 0,
                    'breakdown': collections.defaultdict(list)
                }

            if service_name not in price_mapping:
                price_spec = self._get_service_price(
                    service_name, service_type, products
                )
                price_mapping[service_name] = price_spec

            price_spec = price_mapping[service_name]

            # Convert volume according to unit in price definition.
            volume = float(
                general.convert_to(volume, unit, price_spec['unit'])
            )
            cost = (round(volume * price_spec['rate'], constants.PRICE_DIGITS)
                    if price_spec['rate'] else 0)

            total_cost += cost

            if detailed:
                erp_service_name = "%s.%s" % (region, service_name)

                cost_details[service_type]['total_cost'] = round(
                    (cost_details[service_type]['total_cost'] + cost),
                    constants.PRICE_DIGITS
                )
                cost_details[service_type]['breakdown'][
                    erp_service_name
                ].append(
                    {
                        "resource_name": resource.get('name', ''),
                        "resource_id": res_id,
                        "cost": cost,
                        "quantity": round(volume, 3),
                        "rate": round(price_spec['rate'],
                                      constants.RATE_DIGITS),
                        "unit": price_spec['unit'],
                    }
                )

        result = {
            'total_cost': round(float(total_cost), constants.PRICE_DIGITS)
        }

        if detailed:
            result.update({'details': cost_details})

        return result
