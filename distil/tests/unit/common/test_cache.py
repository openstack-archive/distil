# Copyright (c) 2014 Mirantis Inc.
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
from oslo_cache import core
from oslo_config import cfg

from distil import exceptions as ex
from distil.common import cache
from distil.tests.unit import base


class TestCache(base.DistilTestCase):

    config_file = 'distil.conf'

    def setUp(self):
        super(TestCache, self).setUp()
        self._set_cache(self.conf)
        self.called_count = 0

    def _set_cache(self, conf):
        cache.setup_cache(conf)

    def test_cache(self):
        @cache.memoize
        def test(name):
            self.called_count += 1
            if self.called_count == 1:
                return "hello, Tom"
            if self.called_count == 2:
                return "morning, Tom"
            if self.called_count == 3:
                return "evening, Tom"

        name = 'Tom'
        for x in xrange(0, 2):
            self.assertEqual(test(name), 'hello, Tom')
