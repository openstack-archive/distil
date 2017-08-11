# Copyright (C) 2014 Catalyst IT Ltd
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

from distil.tests.unit import test_interface, utils
from distil import database
from datetime import timedelta


class TestDatabase(test_interface.TestInterface):

    def test_get_from_db(self):
        """Test to ensure the data in the database matches the data entered."""
        num_resources = 32
        num_tenants = 5

        utils.init_db(self.session, num_tenants, num_resources, self.end)

        db = database.Database(self.session)

        for i in range(num_tenants):
            usage = db.usage(self.start, self.start + timedelta(days=60),
                             "tenant_id_" + str(i))
            self.assertEqual(num_resources, usage.count())
