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
import functools
import math
import socket
import warnings
import yaml

from oslo_config import cfg
from oslo_log import log as logging

CONF = cfg.CONF
LOG = logging.getLogger(__name__)
_TRANS_CONFIG = None


def get_transformer_config():
    global _TRANS_CONFIG

    if not _TRANS_CONFIG:
        try:
            with open(CONF.collector.transformer_file) as f:
                _TRANS_CONFIG = yaml.load(f)
        except IOError as e:
            raise e

    return _TRANS_CONFIG


def generate_windows(start, end):
    """Generator for configured hour windows in a given range."""
    window_size = timedelta(hours=CONF.collector.collect_window)
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


def disable_ssl_warnings(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message="A true SSLContext object is not available"
            )
            warnings.filterwarnings(
                "ignore",
                message="Unverified HTTPS request is being made"
            )
            return func(*args, **kwargs)

    return wrapper


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


def get_process_identifier():
    """Gets current running process identifier."""
    return "%s_%s" % (socket.gethostname(), CONF.collector.partitioning_suffix)
