# Copyright 2016 Catalyst IT Ltd
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

from oslo_cache import core
from oslo_config import cfg
from functools import wraps

CACHE_REGION = None
KEY_PREFIX = "distil-"


def register_config(conf):
    core.configure(conf)


def setup_cache(conf):
    global CACHE_REGION
    core.configure(conf)
    region = core.create_region()
    CACHE_REGION = core.configure_cache_region(conf, region)


def _keygen(*args, **kwargs):
    key = KEY_PREFIX
    for arg in args:
        key += str(arg)

    for kwarg in kwargs:
        key += str(kwarg)

    return key


# TODO(flwang): We're recreating wheels, because the way documenting on
# https://docs.openstack.org/oslo.cache/latest/user/usage.html doesn't work for
# us. We will revisit this to replace this decorator when it's sorted out.
def memoize(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        key = _keygen(function.__name__, *args, **kwargs)
        value = CACHE_REGION.get(key)
        if value is core.NO_VALUE:
            value = function(*args, **kwargs)
            CACHE_REGION.set(key, value)
        return value
    return wrapper
