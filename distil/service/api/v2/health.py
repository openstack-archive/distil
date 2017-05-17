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

from datetime import datetime
from datetime import timedelta

from oslo_config import cfg
from oslo_log import log as logging
from distil.db import api as db_api
from distil.common import openstack

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


def get_health():
    """Get health status of distil.

    Currently, we only check usage collection to achieve feature parity with
    current monitoring requirements.

    In future, we could add running status for ERP system, etc.
    """
    result = {}

    projects_keystone = openstack.get_projects()
    keystone_projects = [t['id'] for t in projects_keystone]

    threshold = datetime.utcnow() - timedelta(days=1)

    failed_projects = db_api.project_get_all(
        id={'op': 'in', 'value': keystone_projects},
        last_collected={'op': 'lte', 'value': threshold}
    )

    failed_count = len(failed_projects)

    if failed_count == 0:
        result['usage_collection'] = {
            'status': 'OK',
            'msg': 'Tenant usage successfully collected and up-to-date.'
        }
    else:
        result['usage_collection'] = {
            'status': 'FAIL',
            'msg': 'Failed to collect usage for %s projects.' % failed_count
        }

    return result
