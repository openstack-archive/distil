# Copyright (c) 2017 Catalyst IT Ltd.
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

from distil.common import cache
from distil.common import openstack
from distil.erp import utils as erp_utils

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


def get_credits(project_id):
    keystone_client = openstack.get_keystone_client()
    project_name = keystone_client.projects.get(project_id).name
    erp_driver = erp_utils.load_erp_driver(CONF)
    return erp_driver.get_credits(project_name, datetime.datetime.now())
