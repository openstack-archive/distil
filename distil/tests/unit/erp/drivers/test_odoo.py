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

import mock

from collections import namedtuple

from distil.erp.drivers import odoo
from distil.tests.unit import base

REGION = namedtuple('Region', ['id'])

PRODUCTS = {'11': {'name_template': 'nz-1.c1.c1r1',
                 'lst_price': 0.00015,
                 'default_code': 'hour',
                 'description': '1 CPU, 1GB RAM'},
            '22': {'name_template': 'nz-1.n1.router',
                 'lst_price': 0.00025,
                 'default_code': 'hour',
                 'description': 'Router'},
            '33': {'name_template': 'nz-1.b1.volume',
                 'lst_price': 0.00035,
                 'default_code': 'hour',
                 'description': 'Block storage'},
            '44': {'name_template': 'nz-1.o1.object',
                 'lst_price': 0.00045,
                 'default_code': 'hour',
                 'description': 'Object storage'}}

class TestOdooDriver(base.DistilTestCase):

    config_file = 'distil.conf'

    def setUp(self):
        super(TestOdooDriver, self).setUp()  

    @mock.patch('odoorpc.ODOO')
    @mock.patch('distil.common.openstack.get_regions')
    def test_get_products(self, mock_get_regions, mock_odoo):
        mock_get_regions.return_value = [REGION(id='nz-1'),
                                         REGION(id='nz-2')]

        odoodriver = odoo.OdooDriver(self.conf)

        def _category_search(filters):
            for filter in filters:
                if filter[0] == 'name' and filter[2] == 'Compute':
                    return ['1']
                if filter[0] == 'name' and filter[2] == 'Network':
                    return ['2']
                if filter[0] == 'name' and filter[2] == 'Block Storage':
                    return ['3']
                if filter[0] == 'name' and filter[2] == 'Object Storage':
                    return ['4']

        def _product_search(filters):
            for filter in filters:
                if filter[0] == 'categ_id' and filter[2] == '1':
                    return ['11']
                if filter[0] == 'categ_id' and filter[2] == '2':
                    return ['22']
                if filter[0] == 'categ_id' and filter[2] == '3':
                    return ['33']
                if filter[0] == 'categ_id' and filter[2] == '4':
                    return ['44']

        def _odoo_execute(model, method, *args):
            products = []
            for id in args[0]:
                products.append(PRODUCTS[id])
            return products
      

        odoodriver.odoo.execute = _odoo_execute
        odoodriver.category = mock.Mock()
        odoodriver.category.search = _category_search
        odoodriver.product = mock.Mock()
        odoodriver.product.search = _product_search

        products = odoodriver.get_products(regions=['nz_1'])
        self.assertEqual({'nz-1': {'block storage': [{'description':
                                                      'Block storage',
                                                      'price': 0.00035,
                                                      'resource': 'b1.volume',
                                                      'unit': 'hour'}],
                                   'compute': [{'description':
                                                '1 CPU, 1GB RAM',
                                                'price': 0.00015,
                                                'resource': 'c1.c1r1',
                                                'unit': 'hour'}],
                                   'network': [{'description': 'Router',
                                                'price': 0.00025,
                                                'resource': 'n1.router',
                                                'unit': 'hour'}],
                                   'object storage': [{'description':
                                                       'Object storage',
                                                       'price': 0.00045,
                                                       'resource': 'o1.object',
                                                       'unit': 'hour'}]}},
                         products)
