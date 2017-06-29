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
import json

import odoorpc
from oslo_log import log

from distil.common import cache
from distil.common import general
from distil.common import openstack
from distil.erp import driver
from distil import exceptions

LOG = log.getLogger(__name__)

PRODUCT_CATEGORY = ('Compute', 'Network', 'Block Storage', 'Object Storage')


class OdooDriver(driver.BaseDriver):
    def __init__(self, conf):
        self.odoo = odoorpc.ODOO(conf.odoo.hostname,
                                 protocol=conf.odoo.protocol,
                                 port=conf.odoo.port,
                                 version=conf.odoo.version)
        self.odoo.login(conf.odoo.database, conf.odoo.user, conf.odoo.password)

        self.region_mapping = {}
        self.reverse_region_mapping = {}

        # NOTE(flwang): This is not necessary for most of cases, but just in
        # case some cloud providers are using different region name formats in
        # Keystone and Odoo.
        if conf.odoo.region_mapping:
            regions = conf.odoo.region_mapping.split(',')
            self.region_mapping = dict(
                [(r.split(":")[0].strip(),
                  r.split(":")[1].strip())
                 for r in regions]
            )
            self.reverse_region_mapping = dict(
                [(r.split(":")[1].strip(),
                  r.split(":")[0].strip())
                 for r in regions]
            )

        self.conf = conf
        self.order = self.odoo.env['sale.order']
        self.orderline = self.odoo.env['sale.order.line']
        self.tenant = self.odoo.env['cloud.tenant']
        self.partner = self.odoo.env['res.partner']
        self.pricelist = self.odoo.env['product.pricelist']
        self.product = self.odoo.env['product.product']
        self.category = self.odoo.env['product.category']
        self.invoice = self.odoo.env['account.invoice']
        self.invoice_line = self.odoo.env['account.invoice.line']
        self.credit = self.odoo.env['cloud.credit']

        self.product_catagory_mapping = {}

    @cache.memoize
    def get_products(self, regions=[]):
        self.product_catagory_mapping.clear()
        odoo_regions = []

        if not regions:
            regions = [r.id for r in openstack.get_regions()]
        for r in regions:
            odoo_regions.append(self.region_mapping.get(r, r))

        LOG.debug('Get products for regions in Odoo: %s', odoo_regions)

        prices = {}
        try:
            # NOTE(lingxian): We have to query all products from all regions
            # as Odoo doesn't support search by 'display_name'.
            c = self.category.search([('name', 'in', PRODUCT_CATEGORY)])
            product_ids = self.product.search(
                [('categ_id', 'in', c),
                 ('sale_ok', '=', True),
                 ('active', '=', True)]
            )
            products = self.product.read(product_ids)

            for region in odoo_regions:
                # Ensure returned region name is same with what user see from
                # Keystone.
                actual_region = self.reverse_region_mapping.get(region, region)
                prices[actual_region] = collections.defaultdict(list)

                for product in products:
                    if region.upper() not in product['name_template']:
                        continue

                    name = product['name_template'][len(region) + 1:]
                    if 'pre-prod' in name:
                        continue

                    category = product['categ_id'][1].split('/')[-1].strip()

                    self.product_catagory_mapping[product['id']] = category

                    price = round(product['lst_price'], 5)
                    # NOTE(flwang): default_code is Internal Reference on
                    # Odoo GUI
                    unit = product['default_code']
                    desc = product['description']

                    prices[actual_region][category.lower()].append(
                        {'name': name,
                         'price': price,
                         'unit': unit,
                         'description': desc}
                    )

            # Handle object storage product that does not belong to any
            # region in odoo.
            obj_p_name = self.conf.odoo.object_storage_product_name
            obj_s_name = self.conf.odoo.object_storage_service_name

            obj_pids = self.product.search(
                [('name_template', '=', obj_p_name),
                 ('sale_ok', '=', True),
                 ('active', '=', True)]
            )

            if len(obj_pids) > 0:
                obj_p = self.product.browse(obj_pids[0])

                for region in regions:
                    # Ensure returned region name is same with what user see
                    # from Keystone.
                    actual_region = self.reverse_region_mapping.get(
                        region, region)

                    prices[actual_region]['object storage'].append(
                        {'name': obj_s_name,
                         'price': round(obj_p.lst_price, 5),
                         'unit': obj_p.default_code,
                         'description': obj_p.description}
                    )
        except odoorpc.error.Error as e:
            LOG.exception(e)
            return {}

        return prices

    def _get_invoice_detail(self, invoice_id):
        """Get invoice details.

        Return details in the following format:
        {
          'catagory': {
            'total_cost': xxx,
            'breakdown': {
              '<product_name>': [
                {
                  'resource_name': '',
                  'quantity': '',
                  'unit': '',
                  'rate': '',
                  'cost': ''
                }
              ],
              '<product_name>': [
                {
                  'resource_name': '',
                  'quantity': '',
                  'unit': '',
                  'rate': '',
                  'cost': ''
                }
              ]
            }
          }
        }
        """
        detail_dict = {}

        invoice_lines_ids = self.invoice_line.search(
            [('invoice_id', '=', invoice_id)]
        )
        invoice_lines = self.invoice_line.read(invoice_lines_ids)

        for line in invoice_lines:
            line_info = {
                'resource_name': line['name'],
                'quantity': line['quantity'],
                'rate': round(line['price_unit'], 6),
                'unit': line['uos_id'][1],
                'cost': round(line['price_subtotal'], 6)
            }

            # Original product is a string like "[hour] NZ-POR-1.c1.c2r8"
            product = line['product_id'][1].split(']')[1].strip()
            catagory = self.product_catagory_mapping[line['product_id'][0]]

            if catagory not in detail_dict:
                detail_dict[catagory] = {
                    'total_cost': 0,
                    'breakdown': collections.defaultdict(list)
                }

            detail_dict[catagory]['total_cost'] = round(
                (detail_dict[catagory]['total_cost'] + line_info['cost']), 6
            )
            detail_dict[catagory]['breakdown'][product].append(line_info)

        return detail_dict

    def get_invoices(self, start, end, project_id, detailed=False):
        """Get history invoices from Odoo given a time range.

        Return value is in the following format:
        {
          '<billing_date1>': {
            'total_cost': 100,
            'details': {
                ...
            }
          },
          '<billing_date2>': {
            'total_cost': 200,
            'details': {
                ...
            }
          }
        }

        :param start: Start time, a datetime object.
        :param end: End time, a datetime object.
        :param project_id: project ID.
        :param detailed: Get detailed information.
        :return: The history invoices information for each month.
        """
        # Get invoices in time ascending order.
        result = collections.OrderedDict()

        try:
            invoice_ids = self.invoice.search(
                [
                    ('date_invoice', '>=', str(start.date())),
                    ('date_invoice', '<=', str(end.date())),
                    ('comment', 'like', project_id)
                ],
                order='date_invoice'
            )

            if not len(invoice_ids):
                LOG.debug('No history invoices returned from Odoo.')
                return result

            LOG.debug('Found invoices: %s' % invoice_ids)

            # Convert ids from string to int.
            ids = [int(i) for i in invoice_ids]

            invoices = self.odoo.execute(
                'account.invoice',
                'read',
                ids,
                ['date_invoice', 'amount_total']
            )
            for v in invoices:
                result[v['date_invoice']] = {
                    'total_cost': round(v['amount_total'], 2)
                }

                if detailed:
                    # Populate product catagory mapping first. This should be
                    # quick since we cached get_products()
                    if not self.product_catagory_mapping:
                        self.get_products()

                    details = self._get_invoice_detail(v['id'])
                    result[v['date_invoice']].update({'details': details})
        except Exception as e:
            LOG.exception(
                'Error occured when getting invoices from Odoo, '
                'error: %s' % str(e)
            )

            raise exceptions.ERPException(
                'Failed to get invoices from ERP server.'
            )

        return result

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
                    price.update({'rate': s['price'], 'unit': s['unit']})
                    break
        else:
            found = False
            for category, services in products.items():
                for s in services:
                    if s['name'] == service_name:
                        price.update({'rate': s['price'], 'unit': s['unit']})
                        found = True
                        break

            if not found:
                raise exceptions.NotFoundException(
                    'Price not found, service name: %s, service type: %s' %
                    (service_name, service_type)
                )

        return price

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

        odoo_region = self.region_mapping.get(region, region).upper()
        resources = {row.id: json.loads(row.info) for row in resources}

        products = self.get_products([region])[region]
        service_mapping = self._get_service_mapping(products)

        for entry in measurements:
            service_name = entry.get('service')
            volume = entry.get('volume')
            unit = entry.get('unit')
            res_id = entry.get('resource_id')

            # resource_type is the type defined in meter_mappings.yml.
            resource_type = resources[res_id]['type']
            service_type = service_mapping.get(service_name, resource_type)

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
            volume = general.convert_to(volume, unit, price_spec['unit'])
            cost = (round(volume * Decimal(price_spec['rate']), 6)
                    if price_spec['rate'] else 0)

            total_cost += cost

            if detailed:
                odoo_service_name = "%s.%s" % (odoo_region, service_name)

                cost_details[service_type]['total_cost'] = round(
                    (cost_details[service_type]['total_cost'] + cost), 6
                )
                cost_details[service_type]['breakdown'][
                    odoo_service_name
                ].append(
                    {
                        "resource_name": resources[res_id].get('name', ''),
                        "resource_id": res_id,
                        "cost": cost,
                        "quantity": round(volume, 6),
                        "rate": round(price_spec['rate'], 6),
                        "unit": price_spec['unit'],
                    }
                )

        result = {'total_cost': round(total_cost, 2)}
        if detailed:
            result.update({'details': cost_details})

        return result

    def _normalize_credit(self, credit):
        return {"code": credit["code"],
                "type": credit["credit_type_id"][1],
                "start_date": credit["create_date"],
                "expiry_date": credit["expiry_date"],
                "balance": credit["current_balance"],
                "recurring": credit["recurring"]}

    def get_credits(self, project_id, expiry_date):
        ids = self.credit.search(
            [('cloud_tenant.tenant_id', '=', project_id),
             ('expiry_date', '>', expiry_date.isoformat()),
             ('current_balance', '>', 0.0001)])

        return [self._normalize_credit(c) for c in self.credit.read(ids)]
