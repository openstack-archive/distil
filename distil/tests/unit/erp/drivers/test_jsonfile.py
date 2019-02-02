# Copyright (c) 2019 Catalyst Cloud Ltd.
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

from distil.erp.drivers import jsonfile
from distil.tests.unit import base

REGION = namedtuple('Region', ['id'])

PRODUCTS = [
    {
        'id': 1,
        'categ_id': [1, 'All products (.NET) / nz-1 / Compute'],
        'name_template': 'nz-1.c1.c1r1',
        'lst_price': 0.00015,
        'default_code': 'hour',
        'description': '1 CPU, 1GB RAM'
    },
    {
        'id': 2,
        'categ_id': [2, 'All products (.NET) / nz-1 / Network'],
        'name_template': 'nz-1.n1.router',
        'lst_price': 0.00025,
        'default_code': 'hour',
        'description': 'Router'
    },
    {
        'id': 3,
        'categ_id': [1, 'All products (.NET) / nz-1 / Block Storage'],
        'name_template': 'nz-1.b1.volume',
        'lst_price': 0.00035,
        'default_code': 'hour',
        'description': 'Block storage'
    }
]


class TestJsonFileDriver(base.DistilTestCase):
    config_file = 'distil.conf'

    def test_get_products(self):
        pass

    @mock.patch('distil.erp.drivers.jsonfile.JsonFileDriver.get_products')
    def test_get_quotations_without_details(self, mock_get_products):
        mock_get_products.return_value = {
            'nz-1': {
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

        jf = jsonfile.JsonFileDriver(self.conf)
        quotations = jf.get_quotations(
            'nz-1', 'fake_id', measurements=usage, resources=resources
        )

        self.assertEqual(
            {'total_cost': 0.03},
            quotations
        )

    @mock.patch('distil.erp.drivers.jsonfile.JsonFileDriver.get_products')
    def test_get_quotations_with_details(self, mock_get_products):
        mock_get_products.return_value = {
            'nz-1': {
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

        jf = jsonfile.JsonFileDriver(self.conf)
        quotations = jf.get_quotations(
            'nz-1', 'fake_id', measurements=usage, resources=resources,
            detailed=True
        )

        self.assertDictEqual(
            {
                'total_cost': 0.03,
                'details': {
                    'Compute': {
                        'total_cost': 0.01,
                        'breakdown': {
                            'nz-1.c1.c2r16': [
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
                            'nz-1.b1.standard': [
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

    def test_is_healthy(self):
        def _fake_load_products():
            return {'a': 1}
        jf = jsonfile.JsonFileDriver(self.conf)
        jf._load_products = _fake_load_products
        self.assertTrue(jf.is_healthy())

    def test_is_healthy_false(self):
        def _fake_load_products():
            raise Exception()

        jf = jsonfile.JsonFileDriver(self.conf)
        jf._load_products = _fake_load_products
        self.assertFalse(jf.is_healthy())
