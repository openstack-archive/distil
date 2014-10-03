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

from novaclient.v1_1 import client
from cinderclient.v1 import client as cinderclient
from decimal import Decimal
import config
import math

cache = {}


def reset_cache():
    global cache
    cache = {'flavors': {}, 'volume_types': []}


def flavor_name(f_id):
    """Grabs the correct flavor name from Nova given the correct ID."""
    if f_id not in cache['flavors']:
        nova = client.Client(
            config.auth['username'],
            config.auth['password'],
            config.auth['default_tenant'],
            config.auth['end_point'],
            insecure=config.auth['insecure'])

        cache['flavors'][f_id] = nova.flavors.get(f_id).name
    return cache['flavors'][f_id]


def volume_type(volume_type):
    if not cache['volume_types']:
        cinder = cinderclient.Client(
            config.auth['username'],
            config.auth['password'],
            config.auth['default_tenant'],
            config.auth['end_point'],
            insecure=config.auth['insecure'])

        for vtype in cinder.volume_types.list():
            cache['volume_types'].append({'id': vtype.id,
                                          'name': vtype.name})

    for vtype in cache['volume_types']:
        # check name first, as that will be more common
        if vtype['name'] == volume_type:
            return volume_type
        elif vtype['id'] == volume_type:
            return vtype['name']
    return False


def to_gigabytes_from_bytes(value):
    """From Bytes, unrounded."""
    return ((value / Decimal(1024)) / Decimal(1024)) / Decimal(1024)


def to_hours_from_seconds(value):
    """From seconds to rounded hours"""
    return Decimal(math.ceil((value / Decimal(60)) / Decimal(60)))


conversions = {'byte': {'gigabyte': to_gigabytes_from_bytes},
               'second': {'hour': to_hours_from_seconds}}


def convert_to(value, from_unit, to_unit):
    """Converts a given value to the given unit.
       Assumes that the value is in the lowest unit form,
       of the given unit (seconds or bytes).
       e.g. if the unit is gigabyte we assume the value is in bytes"""
    if from_unit == to_unit:
        return value
    return conversions[from_unit][to_unit](value)
