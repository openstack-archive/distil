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

import mock

from distil.erp import utils as erp_utils
from distil.db.sqlalchemy import api as db_api
from distil.service.api.v2 import health
from distil.tests.unit import base


class HealthTest(base.DistilWithDbTestCase):
    def setUp(self):
        super(HealthTest, self).setUp()
        erp_utils._ERP_DRIVER = None

    @mock.patch('distil.common.openstack.get_projects')
    def test_get_health_ok(self, mock_get_projects):
        mock_get_projects.return_value = [
            {'id': '111', 'name': 'project_1', 'description': ''},
            {'id': '222', 'name': 'project_2', 'description': ''},
        ]

        # Insert projects in the database.
        project_1_collect = datetime.utcnow() - timedelta(hours=1)
        db_api.project_add(
            {
                'id': '111',
                'name': 'project_1',
                'description': '',
            },
            project_1_collect
        )
        project_2_collect = datetime.utcnow() - timedelta(hours=2)
        db_api.project_add(
            {
                'id': '222',
                'name': 'project_2',
                'description': '',
            },
            project_2_collect
        )

        ret = health.get_health()

        self.assertEqual('OK', ret['usage_collection'].get('status'))

    @mock.patch('distil.common.openstack.get_projects')
    def test_get_health_fail(self, mock_get_projects):
        mock_get_projects.return_value = [
            {'id': '111', 'name': 'project_1', 'description': ''},
            {'id': '222', 'name': 'project_2', 'description': ''},
        ]

        # Insert projects in the database.
        project_1_collect = datetime.utcnow() - timedelta(days=2)
        db_api.project_add(
            {
                'id': '111',
                'name': 'project_1',
                'description': '',
            },
            project_1_collect
        )
        project_2_collect = datetime.utcnow() - timedelta(hours=25)
        db_api.project_add(
            {
                'id': '222',
                'name': 'project_2',
                'description': '',
            },
            project_2_collect
        )

        ret = health.get_health()

        self.assertEqual('FAIL', ret['usage_collection'].get('status'))
        self.assertIn('2', ret['usage_collection'].get('msg'))

    @mock.patch('odoorpc.ODOO')
    @mock.patch('distil.common.openstack.get_projects')
    def test_get_health_with_erp_abackend_fail(self, mock_get_projects,
                                               mock_odoo):
        new = mock.MagicMock()
        new.db.list.side_effect = Exception('Boom!')
        mock_odoo.return_value = new
        # mock_odoo.side_effect = ValueError
        ret = health.get_health()

        self.assertEqual('FAIL', ret['erp_backend'].get('status'))

    @mock.patch('odoorpc.ODOO')
    @mock.patch('distil.common.openstack.get_projects')
    def test_get_health_with_erp_backend(self, mock_get_projects, mock_odoo):
        ret = health.get_health()

        self.assertEqual('OK', ret['erp_backend'].get('status'))
