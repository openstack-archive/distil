# Copyright (c) 2016 Catalyst IT Ltd.
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

import datetime

from oslo_config import cfg
from oslo_log import log as logging
from distil.utils import odoo
from distil.db import api as db_api
from distil.utils import keystone

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


def get_health():
    health = {}
    ksclient = keystone.KeystoneClient(
        username=CONF.keystone_authtoken.admin_user,
        password=CONF.keystone_authtoken.admin_password,
        tenant_name=CONF.keystone_authtoken.admin_tenant_name,
        auth_url=CONF.keystone_authtoken.auth_uri,
        insecure=CONF.keystone_authtoken.insecure)

    projects_keystone = ksclient.tenants.list()
    project_id_list_keystone = [t.id for t in projects_keystone]
    projects = db_api.project_get_all()

    # NOTE(flwang): Check the last_collected field for each tenant of Distil,
    # if the date is old (has not been updated more than 24 hours) and the
    # tenant is still active in Keystone, we believe it should be investigated.
    failed_collected_count = 0
    for p in projects:
        delta = (datetime.now() - p.last_collected).total_seconds() // 3600
        if delta >= 24 and p.id in project_id_list_keystone:
            failed_collected_count += 1

    # TODO(flwang): The format of health output need to be discussed so that
    # we can get a stable format before it's used in monitor.
    if failed_collected_count == 0:
        health['metrics_collecting'] = {'status': 'OK',
                                        'note': 'All tenants are synced.'}
    else:
        note = ('Failed to collect metrics for %s projects.' %
                failed_collected_count)
        health['metrics_collecting'] = {'status': 'FAIL',
                                        'note': note}

    return health
