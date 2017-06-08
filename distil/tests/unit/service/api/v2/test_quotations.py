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
import json

import mock

from distil.service.api.v2 import quotations
from distil.tests.unit import base


class QuotationsTest(base.DistilWithDbTestCase):
    @mock.patch('distil.erp.drivers.odoo.OdooDriver.get_quotations')
    @mock.patch('distil.db.api.project_get')
    @mock.patch('distil.db.api.usage_get')
    @mock.patch('distil.db.api.resource_get_by_ids')
    @mock.patch('odoorpc.ODOO')
    def test_get_quotations(self, mock_odoo, mock_get_resources,
                            mock_get_usage, mock_get_project,
                            mock_get_quotations):
        self.override_config('keystone_authtoken', region_name='region-1')

        class Project(object):
            def __init__(self, id, name):
                self.id = id
                self.name = name

        mock_get_project.return_value = Project('123', 'fake_project')

        usage = [
            {
                'resource_id': '111',
                'service': 'srv1',
                'volume': 10,
                'unit': 'byte',
            },
            {
                'resource_id': '222',
                'service': 'srv2',
                'volume': 20,
                'unit': 'byte',
            }
        ]
        mock_get_usage.return_value = usage

        class Resource(object):
            def __init__(self, id, info):
                self.id = id
                self.info = info

        res1 = Resource('111', json.dumps({'name': 'resource1'}))
        res2 = Resource('222', json.dumps({'name': 'resource2'}))
        mock_get_resources.return_value = [res1, res2]

        quotations.get_quotations('123', detailed=False)

        mock_get_quotations.assert_called_once_with(
            'region-1', '123',
            measurements=usage,
            resources=[res1, res2],
            detailed=False
        )
