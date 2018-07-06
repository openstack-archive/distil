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
from datetime import timedelta
import hashlib
import json
import os

import mock

from distil.collector import base as collector_base
from distil.common import constants
from distil import config
from distil.db.sqlalchemy import api as db_api
from distil.service import collector
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
        collector.collect_usage(project, [(start_time, end_time)])

        resources = db_api.resource_get_by_ids(project_id, [resource_id_hash])
        res_info = json.loads(resources[0].info)

        self.assertEqual(1, len(resources))
        self.assertEqual(container_name, res_info['name'])

        entries = db_api.usage_get(project_id, start_time, end_time)

        self.assertEqual(1, len(entries))
        self.assertEqual(resource_id_hash, entries[0].resource_id)

    @mock.patch(
        'distil.collector.ceilometer.CeilometerCollector.collect_usage')
    @mock.patch('distil.common.openstack.get_ceilometer_client')
    @mock.patch('distil.common.openstack.get_projects')
    def test_last_collect_new_project(self, mock_get_projects, mock_cclient,
                                      mock_collect_usage):
        self.override_config('collector', include_tenants=['project_3'])

        # Assume project_3 is a new project that doesn't exist in distil db.
        mock_get_projects.return_value = [
            {'id': '111', 'name': 'project_1', 'description': ''},
            {'id': '222', 'name': 'project_2', 'description': ''},
            {'id': '333', 'name': 'project_3', 'description': ''},
        ]

        # Insert 3 projects in the database, including one project which is
        # not in keystone.
        project_0_collect = datetime(2017, 5, 17, 19)
        db_api.project_add(
            {
                'id': '000',
                'name': 'project_0',
                'description': 'deleted',
            },
            project_0_collect
        )
        project_1_collect = datetime(2017, 5, 17, 20)
        db_api.project_add(
            {
                'id': '111',
                'name': 'project_1',
                'description': '',
            },
            project_1_collect
        )
        project_2_collect = datetime(2017, 5, 17, 21)
        db_api.project_add(
            {
                'id': '222',
                'name': 'project_2',
                'description': '',
            },
            project_2_collect
        )

        svc = collector.CollectorService()
        svc.collect_usage()

        mock_collect_usage.assert_called_once_with(
            {'id': '333', 'name': 'project_3', 'description': ''},
            [(project_1_collect, project_1_collect + timedelta(hours=1))]
        )

    @mock.patch(
        'distil.collector.ceilometer.CeilometerCollector.collect_usage')
    @mock.patch('distil.common.openstack.get_ceilometer_client')
    @mock.patch('distil.common.openstack.get_projects')
    def test_last_collect_ignore_project(self, mock_get_projects, mock_cclient,
                                         mock_collect_usage):
        self.override_config('collector', ignore_tenants=['project_2'])

        mock_get_projects.return_value = [
            {'id': '111', 'name': 'project_1', 'description': ''},
            {'id': '222', 'name': 'project_2', 'description': ''},
        ]

        project1_time = datetime(2017, 5, 17, 20)
        db_api.project_add(
            {
                'id': '111',
                'name': 'project_1',
                'description': '',
            },
            project1_time
        )
        project2_time = datetime(2017, 5, 17, 19)
        db_api.project_add(
            {
                'id': '222',
                'name': 'project_2',
                'description': '',
            },
            project2_time
        )

        svc = collector.CollectorService()
        svc.collect_usage()

        mock_collect_usage.assert_called_once_with(
            {'id': '111', 'name': 'project_1', 'description': ''},
            [(project1_time, project1_time + timedelta(hours=1))]
        )

    @mock.patch('distil.common.openstack.get_ceilometer_client')
    @mock.patch('distil.common.openstack.get_projects')
    @mock.patch('distil.db.api.get_project_locks')
    def test_project_order_ascending(self, mock_get_lock, mock_get_projects,
                                     mock_cclient):
        mock_get_projects.return_value = [
            {'id': '111', 'name': 'project_1', 'description': ''},
            {'id': '222', 'name': 'project_2', 'description': ''},
            {'id': '333', 'name': 'project_3', 'description': ''},
            {'id': '444', 'name': 'project_4', 'description': ''},
        ]

        # Insert a project in the database in order to get last_collect time.
        db_api.project_add(
            {
                'id': '111',
                'name': 'project_1',
                'description': '',
            },
            datetime.utcnow() - timedelta(hours=2)
        )

        svc = collector.CollectorService()
        svc.collector = mock.Mock()
        svc.collect_usage()

        expected_list = ['111', '222', '333', '444']
        actual_list = [call_args[0][0]
                       for call_args in mock_get_lock.call_args_list]
        self.assertEqual(expected_list, actual_list)

    @mock.patch('distil.common.openstack.get_ceilometer_client')
    @mock.patch('distil.common.openstack.get_projects')
    @mock.patch('distil.db.api.get_project_locks')
    def test_project_order_descending(self, mock_get_lock, mock_get_projects,
                                      mock_cclient):
        self.override_config('collector', project_order='descending')

        mock_get_projects.return_value = [
            {'id': '111', 'name': 'project_1', 'description': ''},
            {'id': '222', 'name': 'project_2', 'description': ''},
            {'id': '333', 'name': 'project_3', 'description': ''},
            {'id': '444', 'name': 'project_4', 'description': ''},
        ]

        # Insert a project in the database in order to get last_collect time.
        db_api.project_add(
            {
                'id': '111',
                'name': 'project_1',
                'description': '',
            },
            datetime.utcnow() - timedelta(hours=2)
        )

        svc = collector.CollectorService()
        svc.collector = mock.Mock()
        svc.collect_usage()

        expected_list = ['444', '333', '222', '111']
        actual_list = [call_args[0][0]
                       for call_args in mock_get_lock.call_args_list]
        self.assertEqual(expected_list, actual_list)

    @mock.patch('distil.common.openstack.get_ceilometer_client')
    @mock.patch('distil.common.openstack.get_projects')
    @mock.patch('distil.db.api.get_project_locks')
    def test_project_order_random(self, mock_get_lock, mock_get_projects,
                                  mock_cclient):
        self.override_config('collector', project_order='random')

        mock_get_projects.return_value = [
            {'id': '111', 'name': 'project_1', 'description': ''},
            {'id': '222', 'name': 'project_2', 'description': ''},
            {'id': '333', 'name': 'project_3', 'description': ''},
            {'id': '444', 'name': 'project_4', 'description': ''},
        ]

        # Insert a project in the database in order to get last_collect time.
        db_api.project_add(
            {
                'id': '111',
                'name': 'project_1',
                'description': '',
            },
            datetime.utcnow() - timedelta(hours=2)
        )

        svc = collector.CollectorService()
        svc.collector = mock.Mock()
        svc.collect_usage()

        unexpected_list = ['111', '222', '333', '444']
        actual_list = [call_args[0][0]
                       for call_args in mock_get_lock.call_args_list]
        self.assertNotEqual(unexpected_list, actual_list)

    @mock.patch('os.kill')
    @mock.patch('distil.common.openstack.get_ceilometer_client')
    @mock.patch('distil.common.openstack.get_projects')
    def test_collect_with_end_time(self, mock_get_projects, mock_cclient,
                                   mock_kill):
        end_time = datetime.utcnow() + timedelta(hours=0.5)
        end_time_str = end_time.strftime(constants.iso_time)
        self.override_config(collect_end_time=end_time_str)

        mock_get_projects.return_value = [
            {
                'id': '111',
                'name': 'project_1',
                'description': 'description'
            }
        ]
        # Insert the project info in the database.
        db_api.project_add(
            {
                'id': '111',
                'name': 'project_1',
                'description': '',
            },
            datetime.utcnow()
        )

        srv = collector.CollectorService()
        srv.thread_grp = mock.Mock()
        srv.collect_usage()

        self.assertEqual(1, srv.thread_grp.stop.call_count)
        self.assertEqual(1, mock_kill.call_count)
