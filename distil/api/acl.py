# Copyright 2014 Catalyst IT Ltd
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

from keystonemiddleware import auth_token
from keystonemiddleware import opts
from oslo_config import cfg

CONF = cfg.CONF
AUTH_GROUP_NAME = 'keystone_authtoken'


def _register_opts():
    options = []
    keystone_opts = opts.list_auth_token_opts()
    for n in keystone_opts:
        if (n[0] == AUTH_GROUP_NAME):
            options = n[1]
            break

        CONF.register_opts(options, group=AUTH_GROUP_NAME)
        auth_token.CONF = CONF


_register_opts()


def wrap(app, conf):
    """Wrap wsgi application with ACL check."""
    auth_cfg = dict(conf.get(AUTH_GROUP_NAME))
    auth_protocol = auth_token.AuthProtocol(app, conf=auth_cfg)
    return auth_protocol
