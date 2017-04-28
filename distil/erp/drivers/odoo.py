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

        self.conf = conf
        self.order = self.odoo.env['sale.order']
        self.orderline = self.odoo.env['sale.order.line']
        self.tenant = self.odoo.env['cloud.tenant']
        self.partner = self.odoo.env['res.partner']
        self.pricelist = self.odoo.env['product.pricelist']
        self.product = self.odoo.env['product.product']
        self.category = self.odoo.env['product.category']

    def get_products(self, regions=None):
        if not regions:
            regions = [r.id for r in openstack.get_regions()]
            if hasattr(self, 'region_mapping'):
                regions = self.region_mapping.values()

        else:
            if hasattr(self, 'region_mapping'):
                regions = [self.region_mapping.get(r) for r in regions]

        LOG.debug('Get products for regions: %s', regions)

        prices = {}
        try:
            for r in regions:
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
                    name = p['name_template'][len(r) + 1:]
                    if 'pre-prod' in name:
                        continue

                    category = p['categ_id'][1].split('/')[-1].strip()
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
            obj_p_name = self.conf.odoo.object_storage_product_name
            obj_s_name = self.conf.odoo.object_storage_service_name

            obj_pids = self.product.search(
                [('name_template', '=', obj_p_name),
                 ('sale_ok', '=', True),
                 ('active', '=', True)]
            )

            if len(obj_pids) > 0:
                obj_p = self.product.browse(obj_pids[0])

                for r in regions:
                    prices[r]['object storage'].append(
                        {'resource': obj_s_name,
                         'price': round(obj_p.lst_price, 5),
                         'unit': obj_p.default_code,
                         'description': obj_p.description}
                    )
        except odoorpc.error.Error as e:
            LOG.exception(e)
            return {}

        return prices
