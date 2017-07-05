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

import enum

from oslo_config import cfg
from oslo_log import log as logging
from distil.db import api as db_api
from distil.erp import utils as erp_utils
from distil.common import openstack

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


@enum.unique
class Status(enum.IntEnum):
    """Enum of status for a checking item."""
    OK = 1
    FAIL = 0


def get_health():
    """Get health status of distil.

    Check usage collection and connection to ERP.
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
            'status': Status.OK.name,
            'msg': 'Tenant usage successfully collected and up-to-date.'
        }
    else:
        result['usage_collection'] = {
            'status': Status.FAIL.name,
            'msg': 'Failed to collect usage for %s projects.' % failed_count
        }

    try:
        erp_driver = erp_utils.load_erp_driver(CONF)
        if erp_driver.is_healthy():
            result['erp_backend'] = {"status": Status.OK.name,
                                     "msg": "ERP backend works."}
            return result
    except Exception:
        pass

    result['erp_backend'] = {"status": Status.FAIL.name,
                             "msg": "ERP backend doesn't work."}

    return result
