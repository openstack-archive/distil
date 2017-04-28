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

from oslo_config import cfg
from oslo_log import log as logging

from distil.erp import utils as erp_utils
from distil.service.api.v2 import utils

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


def get_invoices(project_id, start, end, detailed=False):
    project, start, end = utils.convert_project_and_range(
        project_id, start, end)

    LOG.info(
        "Get invoices for %s(%s) in range: %s - %s" %
        (project.id, project.name, start, end)
    )

    output = {
        'start': str(start),
        'end': str(end),
        'project_name': project.name,
        'project_id': project.id,
        'invoices': {}
    }

    # Query from ERP.
    erp_driver = erp_utils.load_erp_driver(CONF)
    erp_invoices = erp_driver.get_invoices(
        start,
        end,
        project.id,
        detailed=detailed
    )

    output['invoices'] = erp_invoices

    return output
