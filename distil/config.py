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

from keystoneauth1 import loading as ka_loading
from oslo_cache import core as cache
from oslo_config import cfg
from oslo_log import log
from oslo_utils import uuidutils

from distil import version

CONF = cfg.CONF

DEFAULT_OPTIONS = (
    cfg.IntOpt('port',
               default=9999,
               help='The port for the Distil API server',
               ),
    cfg.StrOpt('host',
               default='0.0.0.0',
               help='The listen IP for the Distil API server',
               ),
    cfg.ListOpt('public_api_routes',
                default=['/', '/v2/products'],
                help='The list of public API routes',
                ),
    cfg.ListOpt('ignore_tenants',
                default=[],
                help=('The tenant name list which will be ignored when '
                      'collecting metrics from Ceilometer.')),
    cfg.StrOpt('erp_driver',
               default='odoo',
               help='The ERP driver used for Distil',
               ),
)

COLLECTOR_OPTS = [
    cfg.IntOpt('periodic_interval', default=3600,
               help=('Interval of usage collection.')),
    cfg.IntOpt('collect_window', default=1,
               help=('Window of usage collection in hours.')),
    cfg.StrOpt('collector_backend', default='ceilometer',
               help=('Data collector.')),
    cfg.IntOpt('max_windows_per_cycle', default=0,
               help=('The maximum number of windows per collecting cycle.')),
    cfg.StrOpt('meter_mappings_file', default='/etc/distil/meter_mappings.yml',
               help=('The meter mappings configuration.')),
    cfg.StrOpt('transformer_file', default='/etc/distil/transformer.yml',
               help=('The transformer configuration.')),
    cfg.ListOpt('include_tenants', default=[],
                help=('Only collect usages for included tenants.')),
    cfg.ListOpt('ignore_tenants', default=[],
                help=('Do not collect usages for ignored tenants.')),
    cfg.ListOpt('trust_sources', default=[],
                help=('The list of resources that handled by collector.')),
    cfg.StrOpt('dawn_of_time', default='2014-04-01 00:00:00',
               help=('The earlist starting time for new tenant.')),
    cfg.StrOpt('partitioning_suffix',
               help=('Collector partitioning group suffix. It is used when '
                     'running multiple collectors in favor of lock.'))
]

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
    cfg.StrOpt('password', secret=True,
               help='Password of Odoo account to login.'),
    cfg.StrOpt('region_mapping',
               help='Region name mappings between Keystone and Odoo. For '
                    'example, '
                    'region_mapping=region1:RegionOne,region2:RegionTwo'),
    cfg.StrOpt('object_storage_product_name',
               default='NZ.o1.standard',
               help='Product name in Odoo for object storage.'),
    cfg.StrOpt('object_storage_service_name',
               default='o1.standard',
               help='Service name for object storage.'),
]

RATER_OPTS = [
    cfg.StrOpt('rater_type', default='odoo',
               help='Rater type, by default it is odoo.'),
    cfg.StrOpt('rate_file_path', default='/etc/distil/rates.csv',
               help='Rate file path, it will be used when the rater_type '
               'is "file".'),
]

AUTH_GROUP = 'keystone_authtoken'
ODOO_GROUP = 'odoo'
COLLECTOR_GROUP = 'collector'
RATER_GROUP = 'rater'


CONF.register_opts(DEFAULT_OPTIONS)
CONF.register_opts(ODOO_OPTS, group=ODOO_GROUP)
CONF.register_opts(COLLECTOR_OPTS, group=COLLECTOR_GROUP)
CONF.register_opts(RATER_OPTS, group=RATER_GROUP)


def list_opts():
    return [
        (ODOO_GROUP, ODOO_OPTS),
        (COLLECTOR_GROUP, COLLECTOR_OPTS),
        (RATER_GROUP, RATER_OPTS),
        (None, DEFAULT_OPTIONS)
    ]


def _register_keystoneauth_opts(conf):
    # Register keystone authentication related options.
    from keystonemiddleware import auth_token  # noqa

    ka_loading.register_auth_conf_options(conf, AUTH_GROUP)


_register_keystoneauth_opts(CONF)

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


def parse_args(args=None, prog=None):
    log.set_defaults()
    log.register_options(CONF)
    CONF(
        args=args,
        project='distil',
        prog=prog,
        version=version.version_info.version_string(),
    )

    ka_loading.load_auth_from_conf_options(CONF, AUTH_GROUP)

    log.setup(CONF, prog)
