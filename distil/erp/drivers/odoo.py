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

import odoorpc
from oslo_log import log

from distil.common import cache
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
            for region in odoo_regions:
                # Ensure returned region name is same with what user see from
                # Keystone.
                actual_region = self.reverse_region_mapping.get(region, region)
                prices[actual_region] = collections.defaultdict(list)

                # FIXME: Odoo doesn't suppport search by 'display_name'.
                c = self.category.search([('name', 'in', PRODUCT_CATEGORY),
                                          ('display_name', 'ilike', region)])
                product_ids = self.product.search([('categ_id', 'in', c),
                                                   ('sale_ok', '=', True),
                                                   ('active', '=', True)])
                products = self.product.read(product_ids)

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
                'rate': line['price_unit'],
                'unit': line['uos_id'][1],
                'cost': round(line['price_subtotal'], 2)
            }

            # Original product is a string like "[hour] NZ-POR-1.c1.c2r8"
            product = line['product_id'][1].split(']')[1].strip()
            catagory = self.product_catagory_mapping[line['product_id'][0]]

            if catagory not in detail_dict:
                detail_dict[catagory] = {
                    'total_cost': 0,
                    'breakdown': collections.defaultdict(list)
                }

            detail_dict[catagory]['total_cost'] += line_info['cost']
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
