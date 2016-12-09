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

import odoorpc

from oslo_config import cfg
from oslo_log import log
from distil.utils import openstack

CONF = cfg.CONF

PRODUCT_CATEGORY = ('Compute', 'Network', 'Block Storage', 'Object Storage')


class Odoo(object):

    def __init__(self):
        self.odoo = odoorpc.ODOO(CONF.odoo.hostname,
                                 protocol=CONF.odoo.protocol,
                                 port=CONF.odoo.port,
                                 version=CONF.odoo.version)

        self.odoo.login(CONF.odoo.database, CONF.odoo.user, CONF.odoo.password)

        # NOTE(flwang): This is not necessary for most of cases, but just in
        # case some cloud providers are using different region name formats in
        # Keystone and Odoo.
        if CONF.odoo.region_mapping:
            regions = CONF.odoo.region_mapping.split(',')
            self.region_mapping = dict([(r.split(":")[0],
                                         r.split(":")[1]) for r in regions])

        self.order = self.odoo.env['sale.order']
        self.orderline = self.odoo.env['sale.order.line']
        self.tenant = self.odoo.env['cloud.tenant']
        self.partner = self.odoo.env['res.partner']
        self.pricelist = self.odoo.env['product.pricelist']
        self.product = self.odoo.env['product.product']
        self.category = self.odoo.env['product.category']

    def get_prices(self, regions):
        if not regions:
            regions = [r.id for r in openstack.get_regions()]
            if hasattr(self, 'region_mapping'):
                regions = self.region_mapping.values()

        else:
            if hasattr(self, 'region_mapping'):
                regions = [self.region_mapping.get(r) for r in regions]

        prices = {}
        for r in regions:
            if not r:
                continue
            prices[r] = {}
            for category in PRODUCT_CATEGORY:
                prices[r][category.lower()] = []
                c = self.category.search([('name', '=', category),
                                          ('display_name', 'ilike', r)])
                product_ids = self.product.search([('categ_id', '=', c[0]),
                                                   ('sale_ok', '=', True),
                                                   ('active', '=', True)])
                products = self.odoo.execute('product.product',
                                             'read',
                                             product_ids)
                for p in products:
                    name = p['name_template'][len(r) + 1:]
                    if 'pre-prod' in name:
                        continue
                    price = round(p['lst_price'], 5)
                    # NOTE(flwang): default_code is Internal Reference on Odoo
                    # GUI
                    unit = p['default_code']
                    desc = p['description']
                    prices[r][category.lower()].append({'resource': name,
                                                        'price': price,
                                                        'unit': unit,
                                                        'description': desc})

        return prices
