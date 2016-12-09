# Copyright (c) 2013 Mirantis Inc.
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

import flask
import mock
from oslotest import base

from distil import context


class DistilTestCase(base.BaseTestCase):

    def setUp(self):
        super(DistilTestCase, self).setUp()
        self.setup_context()

    def setup_context(self, username="test_user", tenant_id="tenant_1",
                      auth_token="test_auth_token", tenant_name='test_tenant',
                      service_catalog=None, **kwargs):
        self.addCleanup(context.set_ctx,
                        context.ctx() if context.has_ctx() else None)

        context.set_ctx(context.RequestContext(
            username=username, tenant_id=tenant_id,
            auth_token=auth_token, service_catalog=service_catalog or {},
            tenant_name=tenant_name, **kwargs))


class DistilWithDbTestCase(DistilTestCase):
    def setUp(self):
        super(DistilWithDbTestCase, self).setUp()

        self.override_config('connection', "sqlite://", group='database')
        db_api.setup_db()
        self.addCleanup(db_api.drop_db)
