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
from datetime import datetime

import mock

from distil.erp.drivers import odoo
from distil.tests.unit import base

REGION = namedtuple('Region', ['id'])

PRODUCTS = [
    {'categ_id': [1, 'All products (.NET) / nz_1 / Compute'],
     'name_template': 'NZ-1.c1.c1r1',
     'lst_price': 0.00015,
     'default_code': 'hour',
     'description': '1 CPU, 1GB RAM'},
    {'categ_id': [2, 'All products (.NET) / nz_1 / Network'],
     'name_template': 'NZ-1.n1.router',
     'lst_price': 0.00025,
     'default_code': 'hour',
     'description': 'Router'},
    {'categ_id': [1, 'All products (.NET) / nz_1 / Block Storage'],
     'name_template': 'NZ-1.b1.volume',
     'lst_price': 0.00035,
     'default_code': 'hour',
     'description': 'Block storage'}
]


class TestOdooDriver(base.DistilTestCase):
    config_file = 'distil.conf'

    @mock.patch('odoorpc.ODOO')
    def test_get_products(self, mock_odoo):

        odoodriver = odoo.OdooDriver(self.conf)
        odoodriver.product.search.return_value = []
        odoodriver.product.read.return_value = PRODUCTS

        products = odoodriver.get_products(regions=['nz_1'])

        self.assertEqual(
            {
                'nz_1': {
                    'block storage': [{'description': 'Block storage',
                                       'price': 0.00035,
                                       'name': 'b1.volume',
                                       'unit': 'hour'}],
                    'compute': [{'description': '1 CPU, 1GB RAM',
                                 'price': 0.00015,
                                 'name': 'c1.c1r1',
                                 'unit': 'hour'}],
                    'network': [{'description': 'Router',
                                 'price': 0.00025,
                                 'name': 'n1.router',
                                 'unit': 'hour'}]
                }
            },
            products
        )

    @mock.patch('odoorpc.ODOO')
    def test_get_invoices_without_details(self, mock_odoo):
        start = datetime(2017, 3, 1)
        end = datetime(2017, 5, 1)
        fake_project = '123'

        odoodriver = odoo.OdooDriver(self.conf)
        odoodriver.invoice.search.return_value = ['1', '2']
        odoodriver.odoo.execute.return_value = [
            {'date_invoice': '2017-03-31', 'amount_total': 10},
            {'date_invoice': '2017-04-30', 'amount_total': 20}
        ]

        invoices = odoodriver.get_invoices(start, end, fake_project)

        self.assertEqual(
            {
                '2017-03-31': {'total_cost': 10},
                '2017-04-30': {'total_cost': 20}
            },
            invoices
        )

    @mock.patch('odoorpc.ODOO')
    def test_get_invoices_with_details(self, mock_odoo):
        start = datetime(2017, 3, 1)
        end = datetime(2017, 5, 1)
        fake_project = '123'

        odoodriver = odoo.OdooDriver(self.conf)
        odoodriver.invoice.search.return_value = ['1', '2']
        odoodriver.invoice_line.read.side_effect = [
            [
                {
                    'name': 'resource1',
                    'quantity': 100,
                    'price_unit': 0.01,
                    'uos_id': [1, 'Gigabyte-hour(s)'],
                    'price_subtotal': 10,
                    'product_id': [1, '[hour] NZ-POR-1.c1.c2r8']
                }
            ],
            [
                {
                    'name': 'resource2',
                    'quantity': 200,
                    'price_unit': 0.01,
                    'uos_id': [1, 'Gigabyte-hour(s)'],
                    'price_subtotal': 20,
                    'product_id': [1, '[hour] NZ-POR-1.c1.c2r8']
                }
            ]
        ]
        odoodriver.odoo.execute.return_value = [
            {'id': 1, 'date_invoice': '2017-03-31', 'amount_total': 10},
            {'id': 2, 'date_invoice': '2017-04-30', 'amount_total': 20}
        ]

        invoices = odoodriver.get_invoices(
            start, end, fake_project, detailed=True
        )

        self.assertEqual(
            {
                '2017-03-31': {
                    'total_cost': 10,
                    'details': {
                        'NZ-POR-1.c1.c2r8': [{
                            "cost": 10,
                            "quantity": 100,
                            "rate": 0.01,
                            "resource_name": "resource1",
                            "unit": "Gigabyte-hour(s)"
                        }]
                    }
                },
                '2017-04-30': {
                    'total_cost': 20,
                    'details': {
                        'NZ-POR-1.c1.c2r8': [{
                            "cost": 20,
                            "quantity": 200,
                            "rate": 0.01,
                            "resource_name": "resource2",
                            "unit": "Gigabyte-hour(s)"
                        }]
                    }
                }
            },
            invoices
        )
