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
import hashlib
import json
import os

import mock

from distil.collector import base as collector_base
from distil.db.sqlalchemy import api as db_api
from distil.tests.unit import base


class CollectorTest(base.DistilWithDbTestCase):
    def setUp(self):
        super(CollectorTest, self).setUp()

        meter_mapping_file = os.path.join(
            os.environ["DISTIL_TESTS_CONFIGS_DIR"],
            'meter_mappings.yaml'
        )
        self.conf.set_default(
            'meter_mappings_file',
            meter_mapping_file,
            group='collector'
        )

        transformer_file = os.path.join(
            os.environ["DISTIL_TESTS_CONFIGS_DIR"],
            'transformer.yaml'
        )
        self.conf.set_default(
            'transformer_file',
            transformer_file,
            group='collector'
        )

    @mock.patch('distil.collector.base.BaseCollector.get_meter')
    def test_collect_swift_resource_id(self, mock_get_meter):
        project_id = 'fake_project_id'
        project_name = 'fake_project'
        project = {'id': project_id, 'name': project_name}
        start_time = datetime.strptime(
            '2017-02-27 00:00:00',
            "%Y-%m-%d %H:%M:%S"
        )
        end_time = datetime.strptime(
            '2017-02-27 01:00:00',
            "%Y-%m-%d %H:%M:%S"
        )

        # Add project to db in order to satisfy the foreign key constraint of
        # UsageEntry
        db_api.project_add(
            {
                'id': project_id,
                'name': 'fake_project',
                'description': 'project for test'
            }
        )

        container_name = 'my_container'
        resource_id = '%s/%s' % (project_id, container_name)
        resource_id_hash = hashlib.md5(resource_id.encode('utf-8')).hexdigest()

        mock_get_meter.return_value = [
            {
                'resource_id': resource_id,
                'source': 'openstack',
                'volume': 1024
            }
        ]

        collector = collector_base.BaseCollector()
        collector.collect_usage(project, start_time, end_time)

        resources = db_api.resource_get_by_ids(project_id, [resource_id_hash])
        res_info = json.loads(resources[0].info)

        self.assertEquals(1, len(resources))
        self.assertEquals(container_name, res_info['name'])

        entries = db_api.usage_get(project_id, start_time, end_time)

        self.assertEquals(1, len(entries))
        self.assertEquals(resource_id_hash, entries[0].resource_id)
