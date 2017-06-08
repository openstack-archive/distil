# Copyright (C) 2017 Catalyst IT Ltd
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import mock

from distil.service.api.v2 import products
from distil.tests.unit import base


class ProductsTest(base.DistilTestCase):
    @mock.patch('distil.erp.drivers.odoo.OdooDriver.get_products')
    @mock.patch('odoorpc.ODOO')
    def test_get_products(self, mock_odoo, mock_get_products):
        fake_region = 'nz-1'

        products.get_products([fake_region])

        mock_get_products.assert_called_once_with([fake_region])
