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

from collections import namedtuple
from datetime import date

import mock

from distil.erp.drivers import odoo
from distil.tests.unit import base

REGION = namedtuple('Region', ['id'])

PRODUCTS = [
    {'categ_id': [1, 'All products (.NET) / nz_1 / Compute'],
     'name_template': 'nz-1.c1.c1r1',
     'lst_price': 0.00015,
     'default_code': 'hour',
     'description': '1 CPU, 1GB RAM'},
    {'categ_id': [2, 'All products (.NET) / nz_1 / Network'],
     'name_template': 'nz-1.n1.router',
     'lst_price': 0.00025,
     'default_code': 'hour',
     'description': 'Router'},
    {'categ_id': [1, 'All products (.NET) / nz_1 / Block Storage'],
     'name_template': 'nz-1.b1.volume',
     'lst_price': 0.00035,
     'default_code': 'hour',
     'description': 'Block storage'},
    {'categ_id': [1, 'All products (.NET) / nz_1 / Object storage'],
     'name_template': 'nz-1.o1.object',
     'lst_price': 0.00045,
     'default_code': 'hour',
     'description': 'Object storage'}
]

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
        odoodriver.odoo.execute.return_value = PRODUCTS

        products = odoodriver.get_products(regions=['nz_1'])
        self.assertEqual(
            {
                'nz-1':
                    {'block storage': [{'description': 'Block storage',
                                        'price': 0.00035,
                                        'resource': 'b1.volume',
                                        'unit': 'hour'}],
                     'compute': [{'description': '1 CPU, 1GB RAM',
                                  'price': 0.00015,
                                  'resource': 'c1.c1r1',
                                  'unit': 'hour'}],
                     'network': [{'description': 'Router',
                                  'price': 0.00025,
                                  'resource': 'n1.router',
                                  'unit': 'hour'}],
                     'object storage': [{'description': 'Object storage',
                                         'price': 0.00045,
                                         'resource': 'o1.object',
                                         'unit': 'hour'}]
                     }
            },
            products
        )

    @mock.patch('odoorpc.ODOO')
    def test_get_costs(self, mock_odoo):
        bill_dates = ['2016-12-31', '2017-01-31']

        odoodriver = odoo.OdooDriver(self.conf)
        odoodriver.invoice.search.return_value = ['1', '2']
        odoodriver.odoo.execute.return_value = [
            {
                'date_invoice': bill_dates[0],
                'id': 1,
                'amount_total': 10
            },
            {
                'date_invoice': bill_dates[1],
                'id': 2,
                'amount_total': 20
            }
        ]

        costs = odoodriver.get_costs(bill_dates, 'fake_project_id')

        expected = [
            {'billing_date': bill_dates[0], 'total_cost': 10},
            {'billing_date': bill_dates[1], 'total_cost': 20}
        ]

        self.assertListEqual(expected, costs)

    @mock.patch('odoorpc.ODOO')
    def test_build_service_name_mapping(self, mock_odoo):
        products = {
            'block storage': [{'description': 'Block storage',
                               'price': 0.00035,
                               'resource': 'b1.volume',
                               'unit': 'hour'}],
            'compute': [{'description': '1 CPU, 1GB RAM',
                         'price': 0.00015,
                         'resource': 'c1.c1r1',
                         'unit': 'hour'}],
            'network': [{'description': 'Router',
                         'price': 0.00025,
                         'resource': 'n1.router',
                         'unit': 'hour'}],
            'object storage': [{'description': 'Object storage',
                                'price': 0.00045,
                                'resource': 'o1.object',
                                'unit': 'hour'}]
        }

        odoodriver = odoo.OdooDriver(self.conf)
        mapping = odoodriver.build_service_name_mapping(products)

        expected = {
            'b1.volume': 'Block Storage',
            'c1.c1r1': 'Compute',
            'n1.router': 'Router',
            'o1.object': 'Object Storage'
        }

        self.assertEqual(expected, mapping)
