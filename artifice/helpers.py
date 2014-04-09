from novaclient.v1_1 import client
from decimal import Decimal
import config
import math

cache = {}


def flavor_name(f_id):
    f_id = int(f_id)

    if f_id not in cache:
        nova = client.Client(
            config.auth['username'],
            config.auth['password'],
            config.auth['default_tenant'],
            config.auth['end_point'],
            service_type="compute",
            insecure=config.auth['insecure'])

        cache[f_id] = nova.flavors.get(f_id).name
    return cache[f_id]


def to_gigabytes(value):
    """From Bytes, unrounded."""
    return ((value / Decimal(1024)) / Decimal(1024)) / Decimal(1024)


def to_hours(value):
    """From seconds to rounded hours"""
    return Decimal(math.ceil((value / Decimal(60)) / Decimal(60)))


conversions = {'gigabyte': to_gigabytes, 'hour': to_hours}


def convert_to(value, unit):
    """Converts a given value to the given unit.
       Assumes that the value is in the lowest unit form,
       of the given unit (seconds or bytes).
       e.g. if the unit is gigabyte we assume the value is in bytes"""
    return conversions[unit](value)
