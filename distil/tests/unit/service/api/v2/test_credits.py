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

from distil.service.api.v2 import credits
from distil.tests.unit import base


class CreditsTest(base.DistilTestCase):

    @mock.patch('distil.erp.utils.load_erp_driver')
    def test_get_credits(self, mock_load_erp_driver):
        fake_credits = [{"code": "3dd294588f15404f8d77bd97e653324b",
                         "recurring": False,
                         "expiry_date": "2017-11-24",
                         "balance": 500,
                         "type": "Cloud Trial Credit",
                         "start_date": "2017-02-14 02:12:40"}]

        def _get_credits(project_name, expiry_date):
            return fake_credits

        mock_erp_driver = mock.MagicMock()
        mock_load_erp_driver.return_value = mock_erp_driver

        mock_erp_driver.get_credits = _get_credits
        project_id = 'fake_project_id'
        result = credits.get_credits(project_id)
        self.assertEqual(fake_credits, result)
