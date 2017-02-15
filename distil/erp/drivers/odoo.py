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
import calendar
import collections
from datetime import datetime

import odoorpc
from oslo_log import log

from distil.erp import driver
from distil.common import openstack

LOG = log.getLogger(__name__)

PRODUCT_CATEGORY = ('Compute', 'Network', 'Block Storage', 'Object Storage')


class OdooDriver(driver.BaseDriver):
    def __init__(self, conf):
        self.odoo = odoorpc.ODOO(conf.odoo.hostname,
                                 protocol=conf.odoo.protocol,
                                 port=conf.odoo.port,
                                 version=conf.odoo.version)
        self.odoo.login(conf.odoo.database, conf.odoo.user, conf.odoo.password)

        # NOTE(flwang): This is not necessary for most of cases, but just in
        # case some cloud providers are using different region name formats in
        # Keystone and Odoo.
        if conf.odoo.region_mapping:
            regions = conf.odoo.region_mapping.split(',')
            self.region_mapping = dict([(r.split(":")[0].strip(),
                                         r.split(":")[1].strip())
                                        for r in regions])

        self.order = self.odoo.env['sale.order']
        self.orderline = self.odoo.env['sale.order.line']
        self.tenant = self.odoo.env['cloud.tenant']
        self.partner = self.odoo.env['res.partner']
        self.pricelist = self.odoo.env['product.pricelist']
        self.product = self.odoo.env['product.product']
        self.category = self.odoo.env['product.category']
        self.invoice = self.odoo.env['account.invoice']

    def get_products(self, regions=None):
        if not regions:
            regions = [r.id for r in openstack.get_regions()]
            if hasattr(self, 'region_mapping'):
                regions = self.region_mapping.values()

        else:
            if hasattr(self, 'region_mapping'):
                regions = [self.region_mapping.get(r) for r in regions]

        prices = {}
        try:
            for r in regions:
                if not r:
                    continue

                prices[r] = collections.defaultdict(list)

                c = self.category.search([('name', 'in', PRODUCT_CATEGORY),
                                          ('display_name', 'ilike', r)])
                product_ids = self.product.search([('categ_id', 'in', c),
                                                   ('sale_ok', '=', True),
                                                   ('active', '=', True)])
                products = self.odoo.execute('product.product',
                                             'read',
                                             product_ids)
                for p in products:
                    category = p['categ_id'][1].split('/')[-1].strip()

                    name = p['name_template'][len(r) + 1:]
                    if 'pre-prod' in name:
                        continue
                    price = round(p['lst_price'], 5)
                    # NOTE(flwang): default_code is Internal Reference on
                    # Odoo GUI
                    unit = p['default_code']
                    desc = p['description']
                    prices[r][category.lower()].append({'resource': name,
                                                        'price': price,
                                                        'unit': unit,
                                                        'description': desc})

            # Handle object storage product that does not belong to any
            # region in odoo.
            obj_pids = self.product.search(
                [('name_template', '=', 'NZ.o1.standard'),
                 ('sale_ok', '=', True),
                 ('active', '=', True)]
            )

            if len(obj_pids) > 0:
                obj_p = self.product.browse(obj_pids[0])

                for r in regions:
                    prices[r]['object storage'].append(
                        {'resource': 'o1.standard',
                         'price': round(obj_p.lst_price, 5),
                         'unit': obj_p.default_code,
                         'description': obj_p.description}
                    )

        except odoorpc.error.Error as e:
            LOG.exception(e)
            return {}

        return prices

    def _get_next_billing_date(self, start):
        year = start.year + 1 if start.month + 1 > 12 else start.year
        month = (start.month + 1) % 12 or 12
        last_day = calendar.monthrange(year, month)[1]

        return datetime(year, month, last_day)

    def _get_billing_date(self, start):
        last_day = calendar.monthrange(start.year, start.month)[1]

        return datetime(start.year, start.month, last_day)

    def _get_bill_dates(self, start, end):
        today = datetime.today()
        bill_date = self._get_billing_date(start)
        bill_dates = []

        while bill_date < end:
            bill_dates.append(str(bill_date.date()))
            bill_date = self._get_next_billing_date(bill_date)

        if bill_date == end and end.date() != today.date():
            bill_dates.append(str(bill_date.date()))

        return bill_dates

    def get_costs(self, start, end, project_id):
        """Get total cost for each billing month from Odoo.

        The billing date in Odoo is the end of each month.

        :param start: Start time, a datetime object.
        :param end: End time, a datetime object.
        :param project_id: Project ID.
        :return: List of dict contains total cost for each month. If it's not
            returned by Odoo, set total cost of that month to 0.
        """
        costs = []
        default = []

        bill_dates = self._get_bill_dates(start, end)

        if not bill_dates:
            return costs

        for d in bill_dates:
            default.append(
                {'billing_date': d, 'total_cost': 0}
            )

        try:
            invoice_ids = self.invoice.search(
                [
                    ('date_invoice', 'in', bill_dates),
                    ('comment', 'like', project_id)
                ],
                order='date_invoice'
            )

            if not len(invoice_ids):
                LOG.debug('No history invoices returned from Odoo.')
                return default

            LOG.debug('Found invoices: %s' % invoice_ids)

            # Convert ids from string to int.
            ids = []
            for i in invoice_ids:
                ids.append(int(i))

            # For 'account.invoice' model, we can not use 'read' with just a
            # list of IDs
            invoices = self.odoo.execute(
                'account.invoice',
                'read',
                ids,
                ['date_invoice', 'amount_total']
            )
        except Exception as e:
            LOG.exception(
                'Error occured when getting invoices from Odoo, '
                'error: %s' % str(e)
            )
            return default

        invoice_dict = {}
        for v in invoices:
            invoice_dict[v['date_invoice']] = round(v['amount_total'], 2)

        for d in bill_dates:
            if d not in invoice_dict:
                costs.append({'billing_date': d, 'total_cost': 0})
            else:
                costs.append(
                    {'billing_date': d, 'total_cost': invoice_dict[d]}
                )

        return costs
