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

from oslo_config import cfg
from oslo_log import log

DEFAULT_OPTIONS = (
    cfg.ListOpt('ignore_tenants', default=[],
                help=(''),),
)

ODOO_OPTS = [
    cfg.StrOpt('version', default='8.0',
               help='Version of Odoo server.'),
    cfg.StrOpt('hostname',
               help='Host name of Odoo server.'),
    cfg.IntOpt('port', default=443,
               help='Port of Odoo server'),
    cfg.StrOpt('protocol', default='jsonrpc+ssl',
               help='Protocol to connect to Odoo server.'),
    cfg.StrOpt('database',
               help='Name of the Odoo database.'),
    cfg.StrOpt('user',
               help='Name of Odoo account to login.'),
    cfg.StrOpt('password',
               help='Password of Odoo account to login.'),
]

ODOO_GROUP = 'odoo'


def config_options():
    return [(None, DEFAULT_OPTIONS),
            (ODOO_GROUP, ODOO_OPTS)]

# This is simply a namespace for global config storage
main = None
rates_config = None
memcache = None
auth = None
collection = None
transformers = None


def setup_config(conf):
    global main
    main = conf['main']
    global rates_config
    rates_config = conf['rates_config']

    # special case to avoid issues with older configs
    try:
        global memcache
        memcache = conf['memcache']
    except KeyError:
        memcache = {'enabled': False}

    global auth
    auth = conf['auth']
    global collection
    collection = conf['collection']
    global transformers
    transformers = conf['transformers']
