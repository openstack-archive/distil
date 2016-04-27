# Copyright (c) 2014 Catalyst IT Ltd
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
from distil.service.api.v2 import prices
from distil.utils import api

LOG = log.getLogger(__name__)

rest = api.Rest('v2', __name__)


@rest.get('/prices')
def prices_get():
    format = api.get_request_args().get('format', None)
    return api.render(prices=prices.get_prices(format=format))


@rest.get('/costs')
def costs_get():
    return api.render(costs=costs.get_costs())