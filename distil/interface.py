import requests
import json
import auth
from constants import date_format
import config
from datetime import timedelta, datetime
from contextlib import contextmanager
import logging as log

import urlparse


@contextmanager
def timed(desc):
    start = datetime.utcnow()
    yield
    end = datetime.utcnow()
    log.debug("%s: %s" % (desc, end - start))


class Interface(object):
    """Interface for talking to openstack components."""
    def __init__(self):
        self.session = requests.Session()

        # This is the Keystone client connection, which provides our
        # OpenStack authentication
        self.auth = auth.Keystone(
            username=config.auth["username"],
            password=config.auth["password"],
            tenant_name=config.auth["default_tenant"],
            auth_url=config.auth["end_point"],
            insecure=config.auth["insecure"],
            region_name=config.main['region']
        )

    @property
    def tenants(self):
        """All the tenants as known by keystone."""
        with timed("fetch tenant list from keystone"):
            _tenants = self.auth.tenants.list()

        tenants = []

        for tenant in _tenants:
            # if this tenant is in the ignore_tenants, then just pretend
            # it doesnt exist at all.
            if tenant.name not in config.main.get('ignore_tenants', []):
                t = Tenant(tenant, self)
                tenants.append(t)
            else:
                log.debug("Ignored tenant %s (%s) due to config." %
                          (tenant.id, tenant.name))

        return tenants


class InterfaceException(Exception):
    pass

window_leadin = timedelta(minutes=10)


def add_dates(start, end):
    return [
        {
            "field": "timestamp",
            "op": "ge",
            "value": start.strftime(date_format)
        },
        {
            "field": "timestamp",
            "op": "lt",
            "value": end.strftime(date_format)
        }
    ]


class Tenant(object):
    """A wrapper object for the tenant recieved from keystone."""
    def __init__(self, tenant, conn):
        self.tenant = tenant
        self.conn = conn            # the Interface object that produced us.

    @property
    def id(self):
        return self.tenant.id

    @property
    def name(self):
        return self.tenant.name

    @property
    def description(self):
        return self.tenant.description

    def usage(self, meter_name, start, end):
        """Queries ceilometer for all the entries in a given range,
           for a given meter, from this tenant."""
        fields = [{'field': 'project_id', 'op': 'eq', 'value': self.tenant.id}]
        fields.extend(add_dates(start - window_leadin, end))

        with timed('fetch global usage for meter %s' % meter_name):
            endpoint = self.conn.auth.get_ceilometer_endpoint()
            r = self.conn.session.get(
                urlparse.urljoin(endpoint, '/v2/meters/%s' % meter_name),
                headers={
                    "X-Auth-Token": self.conn.auth.auth_token,
                    "Content-Type": "application/json"
                },
                data=json.dumps({'q': fields}))

            if r.status_code == 200:
                return json.loads(r.text)
            else:
                raise InterfaceException('%d %s' % (r.status_code, r.text))
