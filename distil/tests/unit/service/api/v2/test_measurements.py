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

from datetime import datetime
import json

import mock

from distil.service.api.v2 import measurements
from distil.tests.unit import base


class MeasurementsTest(base.DistilWithDbTestCase):
    @mock.patch('distil.common.general.convert_project_and_range')
    @mock.patch('distil.db.api.usage_get')
    @mock.patch('distil.db.api.resource_get_by_ids')
    def test_get_measurements(self, mock_get_resources, mock_db_usage_get,
                              mock_convert):
        class Project(object):
            def __init__(self, id, name):
                self.id = id
                self.name = name

        start = datetime.utcnow()
        end = datetime.utcnow()
        mock_convert.return_value = (
            Project('123', 'fake_name'), start, end
        )

        mock_db_usage_get.return_value = [
            {
                'resource_id': '111',
                'service': 'srv1',
                'volume': 10.12,
                'unit': 'byte',
            },
            {
                'resource_id': '222',
                'service': 'srv2',
                'volume': 20.1,
                'unit': 'byte',
            }
        ]

        class Resource(object):
            def __init__(self, id, info):
                self.id = id
                self.info = info

        res1 = Resource('111', json.dumps({'name': 'resource1'}))
        res2 = Resource('222', json.dumps({'name': 'resource2'}))
        mock_get_resources.return_value = [res1, res2]

        project_measures = measurements.get_measurements(
            '123', str(start), str(end)
        )

        self.assertEqual(
            {
                'start': str(start),
                'end': str(end),
                'project_name': 'fake_name',
                'project_id': '123',
                'resources': {
                    '111': {
                        'name': 'resource1',
                        'services': [
                            {'name': 'srv1', 'volume': 10.12, 'unit': 'byte'}
                        ]
                    },
                    '222': {
                        'name': 'resource2',
                        'services': [
                            {'name': 'srv2', 'volume': 20.1, 'unit': 'byte'}
                        ]
                    }
                }
            },
            project_measures
        )
