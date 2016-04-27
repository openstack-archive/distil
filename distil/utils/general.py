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

from datetime import datetime
from datetime import timedelta
from decimal import Decimal
import math
import yaml

from oslo.config import cfg
from novaclient.v1_1 import client

from distil.openstack.common import log as logging

COLLECTOR_OPTS = [
    cfg.StrOpt('transformer_config',
               default='/etc/distil/collector.yaml',
               help='The configuration file of collector',
               ),
]

CONF = cfg.CONF
CONF.register_opts(COLLECTOR_OPTS, group='collector')
cache = {}

LOG = logging.getLogger(__name__)


def get_collector_config():
    # FIXME(flwang): The config should be cached or find a better way to load
    # it dynamically.
    conf = None
    try:
        with open(CONF.collector.transformer_config) as f:
            conf = yaml.load(f)
    except IOError as e:
        raise e
    return conf


def generate_windows(start, end):
    """Generator for configured hour windows in a given range."""
    # FIXME(flwang): CONF.collector.period
    window_size = timedelta(hours=1)
    while start + window_size <= end:
        window_end = start + window_size
        yield start, window_end
        start = window_end


def log_and_time_it(f):
    def decorator(*args, **kwargs):
        start = datetime.utcnow()
        LOG.info('Entering %s at %s' % (f.__name__, start))
        f(*args, **kwargs)
        LOG.info('Exiting %s at %s, elapsed %s' % (f.__name__, 
                                                   datetime.utcnow(),
                                                   datetime.utcnow() - start))
    return decorator


def flavor_name(flavor_id):
    """Grabs the correct flavor name from Nova given the correct ID."""
    # FIXME(flwang): Read the auth info from CONF
    if flavor_id not in cache:
        nova = client.Client()
        cache[flavor_id] = nova.flavors.get(flavor_id).name
    return cache[flavor_id]


def to_gigabytes_from_bytes(value):
    """From Bytes, unrounded."""
    return ((value / Decimal(1024)) / Decimal(1024)) / Decimal(1024)


def to_hours_from_seconds(value):
    """From seconds to rounded hours."""
    return Decimal(math.ceil((value / Decimal(60)) / Decimal(60)))


conversions = {'byte': {'gigabyte': to_gigabytes_from_bytes},
               'second': {'hour': to_hours_from_seconds}}


def convert_to(value, from_unit, to_unit):
    """Converts a given value to the given unit.
       Assumes that the value is in the lowest unit form,
       of the given unit (seconds or bytes).
       e.g. if the unit is gigabyte we assume the value is in bytes
       """
    if from_unit == to_unit:
        return value
    return conversions[from_unit][to_unit](value)
