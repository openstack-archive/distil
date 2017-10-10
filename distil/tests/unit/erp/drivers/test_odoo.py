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
from decimal import Decimal
import mock

from distil.erp.drivers import odoo
from distil.tests.unit import base

REGION = namedtuple('Region', ['id'])

PRODUCTS = [
    {
        'id': 1,
        'categ_id': [1, 'All products (.NET) / nz_1 / Compute'],
        'name_template': 'NZ-1.c1.c1r1',
        'lst_price': 0.00015,
        'default_code': 'hour',
        'description': '1 CPU, 1GB RAM'
    },
    {
        'id': 2,
        'categ_id': [2, 'All products (.NET) / nz_1 / Network'],
        'name_template': 'NZ-1.n1.router',
        'lst_price': 0.00025,
        'default_code': 'hour',
        'description': 'Router'
    },
    {
        'id': 3,
        'categ_id': [1, 'All products (.NET) / nz_1 / Block Storage'],
        'name_template': 'NZ-1.b1.volume',
        'lst_price': 0.00035,
        'default_code': 'hour',
        'description': 'Block storage'
    }
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
                                       'rate': 0.00035,
                                       'name': 'b1.volume',
                                       'unit': 'hour'}],
                    'compute': [{'description': '1 CPU, 1GB RAM',
                                 'rate': 0.00015,
                                 'name': 'c1.c1r1',
                                 'unit': 'hour'}],
                    'network': [{'description': 'Router',
                                 'rate': 0.00025,
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
            {'date_invoice': '2017-03-31', 'amount_total': 10,
             'state': 'paid'},
            {'date_invoice': '2017-04-30', 'amount_total': 20,
             'state': 'open'},
        ]

        invoices = odoodriver.get_invoices(start, end, fake_project)

        self.assertEqual(
            {
                '2017-03-31': {'total_cost': 10, 'status': 'paid'},
                '2017-04-30': {'total_cost': 20, 'status': 'open'}
            },
            invoices
        )

    @mock.patch('odoorpc.ODOO')
    @mock.patch('distil.erp.drivers.odoo.OdooDriver.get_products')
    def test_get_invoices_with_details(self, mock_get_products, mock_odoo):
        start = datetime(2017, 3, 1)
        end = datetime(2017, 5, 1)
        fake_project = '123'

        odoodriver = odoo.OdooDriver(self.conf)
        odoodriver.invoice.search.return_value = ['1', '2']
        odoodriver.invoice_line.read.side_effect = [
            [
                {
                    'name': 'resource1',
                    'quantity': 1,
                    'price_unit': 0.123,
                    'uos_id': [1, 'Gigabyte-hour(s)'],
                    'price_subtotal': 0.123,
                    'product_id': [1, '[hour] NZ-POR-1.c1.c2r8']
                },
                {
                    'name': 'resource2',
                    'quantity': 2,
                    'price_unit': 0.123,
                    'uos_id': [1, 'Gigabyte-hour(s)'],
                    'price_subtotal': 0.246,
                    'product_id': [1, '[hour] NZ-POR-1.c1.c2r8']
                }
            ],
            [
                {
                    'name': 'resource3',
                    'quantity': 653.2345,
                    'price_unit': 0.123,
                    'uos_id': [1, 'Gigabyte-hour(s)'],
                    'price_subtotal': 0.369,
                    'product_id': [1, '[hour] NZ-POR-1.c1.c2r8']
                },
                {
                    'name': 'resource4',
                    'quantity': 4,
                    'price_unit': 0.123,
                    'uos_id': [1, 'Gigabyte-hour(s)'],
                    'price_subtotal': 0.492,
                    'product_id': [1, '[hour] NZ-POR-1.c1.c2r8']
                },
                {
                    "name": "Development Grant",
                    "quantity": 1,
                    "price_unit": -0.1,
                    'uos_id': [1, 'Unit(s)'],
                    "price_subtotal": -0.1,
                    'product_id': [4, 'cloud-dev-grant']
                }
            ]
        ]
        odoodriver.odoo.execute.return_value = [
            {'id': 1, 'date_invoice': '2017-03-31', 'amount_total': 0.371,
             'state': 'paid'},
            {'id': 2, 'date_invoice': '2017-04-30', 'amount_total': 0.759,
             'state': 'open'}
        ]
        odoodriver.product_category_mapping = {
            1: 'Compute',
            4: 'Discounts'
        }

        invoices = odoodriver.get_invoices(
            start, end, fake_project, detailed=True
        )

        # The category total price is get from odoo. The total price of
        # specific product is calculated based on invoice detail in odoo.
        self.assertEqual(
            {
                '2017-03-31': {
                    'total_cost': 0.37,
                    'status': 'paid',
                    'details': {
                        'Compute': {
                            'total_cost': 0.37,
                            'breakdown': {
                                'NZ-POR-1.c1.c2r8': [
                                    {
                                        "cost": 0.12,
                                        "quantity": 1,
                                        "rate": 0.123,
                                        "resource_name": "resource1",
                                        "unit": "Gigabyte-hour(s)"
                                    },
                                    {
                                        "cost": 0.25,
                                        "quantity": 2,
                                        "rate": 0.123,
                                        "resource_name": "resource2",
                                        "unit": "Gigabyte-hour(s)"
                                    }
                                ]
                            }
                        }
                    }
                },
                '2017-04-30': {
                    'total_cost': 0.76,
                    'status': 'open',
                    'details': {
                        "Discounts":{
                            "total_cost": -0.1,
                            "breakdown":{
                                'cloud-dev-grant': [
                                    {
                                        'quantity': 1.0,
                                        'unit': 'Unit(s)',
                                        'cost': -0.1,
                                        'resource_name': 'Development Grant',
                                        'rate': -0.1}
                                ]
                            }
                        },
                        'Compute': {
                            'total_cost': 0.86,
                            'breakdown': {
                                'NZ-POR-1.c1.c2r8': [
                                    {
                                        "cost": 0.37,
                                        "quantity": 653.235,
                                        "rate": 0.123,
                                        "resource_name": "resource3",
                                        "unit": "Gigabyte-hour(s)"
                                    },
                                    {
                                        "cost": 0.49,
                                        "quantity": 4,
                                        "rate": 0.123,
                                        "resource_name": "resource4",
                                        "unit": "Gigabyte-hour(s)"
                                    }
                                ]
                            }
                        }
                    }
                }
            },
            invoices
        )

    @mock.patch('odoorpc.ODOO')
    @mock.patch('distil.erp.drivers.odoo.OdooDriver.get_products')
    def test_get_quotations_without_details(self, mock_get_products,
                                            mock_odoo):
        mock_get_products.return_value = {
            'nz_1': {
                'Compute': [
                    {
                        'name': 'c1.c2r16', 'description': 'c1.c2r16',
                        'rate': 0.01, 'unit': 'hour'
                    }
                ],
                'Block Storage': [
                    {
                        'name': 'b1.standard', 'description': 'b1.standard',
                        'rate': 0.02, 'unit': 'gigabyte'
                    }
                ]
            }
        }

        class Resource(object):
            def __init__(self, id, info):
                self.id = id
                self.info = info

        resources = [
            Resource(1, '{"name": "", "type": "Volume"}'),
            Resource(2, '{"name": "", "type": "Virtual Machine"}')
        ]

        usage = [
            {
                'service': 'b1.standard',
                'resource_id': 1,
                'volume': 1024 * 1024 * 1024,
                'unit': 'byte',
            },
            {
                'service': 'c1.c2r16',
                'resource_id': 2,
                'volume': 3600,
                'unit': 'second',
            }
        ]

        odoodriver = odoo.OdooDriver(self.conf)
        quotations = odoodriver.get_quotations(
            'nz_1', 'fake_id', measurements=usage, resources=resources
        )

        self.assertEqual(
            {'total_cost': 0.03},
            quotations
        )

    @mock.patch('odoorpc.ODOO')
    @mock.patch('distil.erp.drivers.odoo.OdooDriver.get_products')
    def test_get_quotations_with_details(self, mock_get_products,
                                         mock_odoo):
        mock_get_products.return_value = {
            'nz_1': {
                'Compute': [
                    {
                        'name': 'c1.c2r16', 'description': 'c1.c2r16',
                        'rate': 0.01, 'unit': 'hour'
                    }
                ],
                'Block Storage': [
                    {
                        'name': 'b1.standard', 'description': 'b1.standard',
                        'rate': 0.02, 'unit': 'gigabyte'
                    }
                ]
            }
        }

        class Resource(object):
            def __init__(self, id, info):
                self.id = id
                self.info = info

        resources = [
            Resource(1, '{"name": "volume1", "type": "Volume"}'),
            Resource(2, '{"name": "instance2", "type": "Virtual Machine"}')
        ]

        usage = [
            {
                'service': 'b1.standard',
                'resource_id': 1,
                'volume': 1024 * 1024 * 1024,
                'unit': 'byte',
            },
            {
                'service': 'c1.c2r16',
                'resource_id': 2,
                'volume': 3600,
                'unit': 'second',
            }
        ]

        odoodriver = odoo.OdooDriver(self.conf)
        quotations = odoodriver.get_quotations(
            'nz_1', 'fake_id', measurements=usage, resources=resources,
            detailed=True
        )

        self.assertDictEqual(
            {
                'total_cost': 0.03,
                'details': {
                    'Compute': {
                        'total_cost': 0.01,
                        'breakdown': {
                            'NZ-1.c1.c2r16': [
                                {
                                    "resource_name": "instance2",
                                    "resource_id": 2,
                                    "cost": 0.01,
                                    "quantity": 1.0,
                                    "rate": 0.01,
                                    "unit": "hour",
                                }
                            ],
                        }
                    },
                    'Block Storage': {
                        'total_cost': 0.02,
                        'breakdown': {
                            'NZ-1.b1.standard': [
                                {
                                    "resource_name": "volume1",
                                    "resource_id": 1,
                                    "cost": 0.02,
                                    "quantity": 1.0,
                                    "rate": 0.02,
                                    "unit": "gigabyte",
                                }
                            ]
                        }
                    }
                }
            },
            quotations
        )

    @mock.patch('odoorpc.ODOO')
    @mock.patch('distil.erp.drivers.odoo.OdooDriver.get_products')
    def test_get_quotations_with_details_windows_vm(self, mock_get_products,
                                                    mock_odoo):
        mock_get_products.return_value = {
            'nz_1': {
                'Compute': [
                    {
                        'name': 'c1.c2r16', 'description': 'c1.c2r16',
                        'rate': 0.01, 'unit': 'hour'
                    },
                    {
                        'name': 'c1.c2r16-windows',
                        'description': 'c1.c2r16-windows',
                        'rate': 0.02, 'unit': 'hour'
                    }
                ],
                'Block Storage': [
                    {
                        'name': 'b1.standard', 'description': 'b1.standard',
                        'rate': 0.02, 'unit': 'gigabyte'
                    }
                ]
            }
        }

        class Resource(object):
            def __init__(self, id, info):
                self.id = id
                self.info = info

        resources = [
            Resource(1, '{"name": "volume1", "type": "Volume"}'),
            Resource(
                2,
                '{"name": "instance2", "type": "Virtual Machine", '
                '"os_distro": "windows"}'
            )
        ]

        class Usage(object):
            def __init__(self, service, resource_id, volume, unit):
                self.service = service
                self.resource_id = resource_id
                self.volume = volume
                self.unit = unit

            def get(self, attr):
                return getattr(self, attr)

        usage = [
            Usage('b1.standard', 1, 1024 * 1024 * 1024, 'byte'),
            Usage('c1.c2r16', 2, 3600, 'second')
        ]

        odoodriver = odoo.OdooDriver(self.conf)
        quotations = odoodriver.get_quotations(
            'nz_1', 'fake_id', measurements=usage, resources=resources,
            detailed=True
        )

        self.assertDictEqual(
            {
                'total_cost': 0.05,
                'details': {
                    'Compute': {
                        'total_cost': 0.03,
                        'breakdown': {
                            'NZ-1.c1.c2r16': [
                                {
                                    "resource_name": "instance2",
                                    "resource_id": 2,
                                    "cost": 0.01,
                                    "quantity": 1.0,
                                    "rate": 0.01,
                                    "unit": "hour",
                                }
                            ],
                            'NZ-1.c1.c2r16-windows': [
                                {
                                    "resource_name": "instance2",
                                    "resource_id": 2,
                                    "cost": 0.02,
                                    "quantity": 1.0,
                                    "rate": 0.02,
                                    "unit": "hour",
                                }
                            ],
                        }
                    },
                    'Block Storage': {
                        'total_cost': 0.02,
                        'breakdown': {
                            'NZ-1.b1.standard': [
                                {
                                    "resource_name": "volume1",
                                    "resource_id": 1,
                                    "cost": 0.02,
                                    "quantity": 1.0,
                                    "rate": 0.02,
                                    "unit": "gigabyte",
                                }
                            ]
                        }
                    }
                }
            },
            quotations
        )

    @mock.patch('odoorpc.ODOO')
    def test_get_credits(self, mock_odoo):
        fake_credits = [{'create_uid': [182, 'OpenStack Testing'],
                         'initial_balance': 500.0,
                         'code': '3dd294588f15404f8d77bd97e653324b',
                         'credit_type_id': [1, 'Cloud Trial Credit'],
                         'name': '3dd294588f15404f8d77bd97e653324b',
                         '__last_update': '2017-05-26 02:16:38',
                         'current_balance': 500.0,
                         'cloud_tenant': [212,
                                          'openstack-dev.catalyst.net.nz'],
                         'write_uid': [98, 'OpenStack Billing'],
                         'expiry_date': '2017-11-24',
                         'write_date': '2017-05-26 02:16:38',
                         'id': 68, 'create_date': '2017-02-14 02:12:40',
                         'recurring': False, 'start_date': '2017-10-23',
                         'display_name': '3dd294588f15404f8d77bd97e653324b'}]

        project_id = 'fake_project_id'
        odoodriver = odoo.OdooDriver(self.conf)
        odoodriver.credit.search.return_value = []
        odoodriver.credit.read.return_value = fake_credits
        credits = odoodriver.get_credits(project_id,
                                         datetime.now())
        self.assertEqual([{"code": "3dd294588f15404f8d77bd97e653324b",
                           "recurring": False,
                           "expiry_date": "2017-11-24",
                           "balance": 500,
                           "type": "Cloud Trial Credit",
                           "start_date": "2017-02-14 02:12:40"}],
                         credits)

    @mock.patch('odoorpc.ODOO')
    def test_is_healthy(self, mock_odoo):
        odoodriver = odoo.OdooDriver(self.conf)
        odoodriver.odoo.db.list.return_value = ["A", "B"]
        self.assertTrue(odoodriver.is_healthy())

    @mock.patch('odoorpc.ODOO')
    def test_is_healthy_false(self, mock_odoo):
        odoodriver = odoo.OdooDriver(self.conf)
        odoodriver.odoo.db.list.side_effect = Exception("Odoo Error!")
        self.assertFalse(odoodriver.is_healthy())
