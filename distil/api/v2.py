# Copyright (c) 2016 Catalyst IT Ltd
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

from dateutil import parser

from oslo_log import log

from distil import exceptions
from distil.api import acl
from distil.service.api.v2 import costs
from distil.service.api.v2 import health
from distil.service.api.v2 import products
from distil.utils import api
from distil.utils import constants
from distil.i18n import _LE

LOG = log.getLogger(__name__)

rest = api.Rest('v2', __name__)


@rest.get('/health')
def health_get():
    try:
        return api.render(health=health.get_health())
    except Exception:
        msg = _LE("Failed to get health status, please try again later.")
        return api.render(status=400, error=msg)


@rest.get('/products')
def products_get():
    os_regions = api.get_request_args().get('regions', None)
    regions = os_regions.split(',') if os_regions else None
    try:
        return api.render(products=products.get_products(regions))
    except Exception as e:
        return api.render(status=400, error=str(e))


def _get_usage_args():
    # NOTE(flwang): Get 'tenant' first for backward compatibility.
    tenant_id = api.get_request_args().get('tenant', None)
    project_id = api.get_request_args().get('project_id', tenant_id)
    start = api.get_request_args().get('start', None)
    end = api.get_request_args().get('end', None)
    return project_id, start, end


@rest.get('/costs')
@acl.enforce("rating:costs:get")
def costs_get():
    project_id, start, end = _get_usage_args()
    try:
        # NOTE(flwang): Here using 'usage' instead of 'costs' for backward
        # compatibility.
        return api.render(usage=costs.get_costs(project_id, start, end))
    except (exceptions.DateTimeException, exceptions.NotFoundException) as e:
        return api.render(status=400, error=str(e))


@rest.get('/usages')
@acl.enforce("rating:usages:get")
def usage_get():
    project_id, start, end = _get_usage_args()
    try:
        return api.render(usage=costs.get_usage(project_id, start, end))
    except (exceptions.DateTimeException, exceptions.NotFoundException) as e:
        return api.render(status=400, error=str(e))
