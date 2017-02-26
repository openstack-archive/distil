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

from distil.db.sqlalchemy import api as db_api
from distil.tests.unit import base


class ProjectLockTest(base.DistilWithDbTestCase):
    def test_with_project_lock(self):
        project_id = 'fake_project_id'
        owner = 'fake_owner'

        with db_api.project_lock(project_id, owner):
            # Make sure that within 'with' section the lock record exists.
            self.assertEqual(1, len(db_api.get_project_locks(project_id)))

        # Make sure that outside 'with' section the lock record does not exist.
        self.assertEqual(0, len(db_api.get_project_locks(project_id)))
