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
import os
from oslotest import base
from oslo_config import cfg
from oslo_log import log

from distil.common import cache
from distil import context
from distil import config
from distil.db import api as db_api

class DistilTestCase(base.BaseTestCase):

    config_file = None

    def setUp(self):
        super(DistilTestCase, self).setUp()
        self.setup_context()

        if self.config_file:
            self.conf = self.load_conf(self.config_file)
        else:
            self.conf = cfg.CONF

        cache.setup_cache(self.conf)

        self.conf.register_opts(config.DEFAULT_OPTIONS)
        self.conf.register_opts(config.ODOO_OPTS, group=config.ODOO_GROUP)
        self.conf.register_opts(
            config.COLLECTOR_OPTS, group=config.COLLECTOR_GROUP
        )

    def setup_context(self, username="test_user", tenant_id="tenant_1",
                      auth_token="test_auth_token", tenant_name='test_tenant',
                      service_catalog=None, **kwargs):
        self.addCleanup(context.set_ctx,
                        context.ctx() if context.has_ctx() else None)

        context.set_ctx(context.RequestContext(
            username=username, tenant_id=tenant_id,
            auth_token=auth_token, service_catalog=service_catalog or {},
            tenant_name=tenant_name, **kwargs))

    @classmethod
    def conf_path(cls, filename):
        """Returns the full path to the specified Distil conf file.

        :param filename: Name of the conf file to find (e.g.,
                         'distil_odoo.conf')
        """

        if os.path.exists(filename):
            return filename

        return os.path.join(os.environ["DISTIL_TESTS_CONFIGS_DIR"], filename)

    @classmethod
    def load_conf(cls, filename):
        """Loads `filename` configuration file.

        :param filename: Name of the conf file to find (e.g.,
                         'distil_odoo.conf')

        :returns: Project's config object.
        """
        conf = cfg.CONF
        conf(args=[], default_config_files=[cls.conf_path(filename)])
        return conf

    def override_config(self, group=None, **kw):
        """Override some configuration values.

        The keyword arguments are the names of configuration options to
        override and their values.

        If a group argument is supplied, the overrides are applied to
        the specified configuration option group.

        All overrides are automatically cleared at the end of the current
        test by the tearDown() method.
        """
        for k, v in kw.items():
            self.conf.set_override(k, v, group, enforce_type=True)

    def _my_dir(self):
        return os.path.abspath(os.path.dirname(__file__))


class DistilWithDbTestCase(DistilTestCase):
    def setUp(self):
        super(DistilWithDbTestCase, self).setUp()

        self.conf.set_default('connection', 'sqlite://', group='database')
        db_api.setup_db()
        self.addCleanup(db_api.drop_db)
