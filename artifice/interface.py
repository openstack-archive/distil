import requests
import json
import auth
from ceilometerclient.v2.client import Client as ceilometer
from artifice.models import resources
from constants import date_format
import config
from datetime import timedelta

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


class Artifice(object):
    """Produces billable artifacts"""
    def __init__(self):
        super(Artifice, self).__init__()

        # This is the Keystone client connection, which provides our
        # OpenStack authentication
        self.auth = auth.Keystone(
            username=config.auth["username"],
            password=config.auth["password"],
            tenant_name=config.auth["default_tenant"],
            auth_url=config.auth["end_point"],
            insecure=config.auth["insecure"]
        )

        self.ceilometer = ceilometer(
            config.ceilometer["host"],
            # Uses a lambda as ceilometer apparently wants
            # to use it as a callable?
            token=lambda: self.auth.auth_token,
            insecure=config.auth["insecure"]
        )
        self._tenancy = None

    def tenant(self, id_):
        """
        Returns a Tenant object describing the specified Tenant by
        name, or raises a NotFound error.
        """

        data = self.auth.tenants.get(id_)
        t = Tenant(data, self)
        return t

    @property
    def tenants(self):
        """All the tenants in our system"""
        if not self._tenancy:
            self._tenancy = []
            for tenant in self.auth.tenants.list():
                t = Tenant(tenant, self)
                self._tenancy.append(t)
        return self._tenancy


class Tenant(object):

    def __init__(self, tenant, conn):
        self.tenant = tenant
        # Conn is the niceometer object we were instanced from
        self.conn = conn
        self._meters = set()
        self._resources = None

    @property
    def id(self):
        return self.tenant.id
    @property
    def name(self):
        return self.tenant.name
    @property
    def description(self):
        return self.tenant.description

    def resources(self, start, end):
        date_fields = [
            {"field": "project_id",
             "op": "eq",
             "value": self.tenant.id
             },
        ]
        date_fields.extend(add_dates(start, end))
        resources = self.conn.ceilometer.resources.list(date_fields)

    def usage(self, start, end):
        """
        Usage is the meat of Artifice, returning a dict of location to
        sub-information
        """
        vms = []
        networks = []
        ips = []
        storage = []
        volumes = []

        for resource in self.resources(start, end):
            rels = [link["rel"] for link in resource.links if link["rel"] != 'self']
            if "storage.objects" in rels:
                storage.append(Resource(resource, self.conn))
                pass
            elif "network.incoming.bytes" in rels:
                networks.append(Resource(resource, self.conn))
            elif "volume" in rels:
                volumes.append(Resource(resource, self.conn))
            elif 'instance' in rels:
                vms.append(Resource(resource, self.conn))
            elif 'ip.floating' in rels:
                ips.append(Resource(resource, self.conn))

        region_tmpl = {
            "vms": vms,
            "networks": networks,
            "objects": storage,
            "volumes": volumes,
            "ips": ips
        }

        return Usage(region_tmpl, start, end, self.conn)


class Usage(object):
    """
    This is a dict-like object containing all the datacenters and
    meters available in those datacenters.
    """

    def __init__(self, contents, start, end, conn):
        self.contents = contents
        self.start = start
        self.end = end
        self.conn = conn

        self._vms = []
        self._objects = []
        self._volumes = []
        self._networks = []
        self._ips = []

    def values(self):
        return (self.vms + self.objects + self.volumes +
                self.networks + self.ips)

    @property
    def vms(self):
        if not self._vms:
            vms = []
            for vm in self.contents["vms"]:
                VM = resources.VM(vm, self.start, self.end)
                vms.append(VM)
            self._vms = vms
        return self._vms

    @property
    def objects(self):
        if not self._objects:
            objs = []
            for object_ in self.contents["objects"]:
                obj = resources.Object(object_, self.start, self.end)
                objs.append(obj)
            self._objs = objs
        return self._objs

    @property
    def networks(self):
        if not self._networks:
            networks = []
            for obj in self.contents["networks"]:
                obj = resources.Network(obj, self.start, self.end)
                networks.append(obj)
            self._networks = networks
        return self._networks

    @property
    def ips(self):
        if not self._ips:
            ips = []
            for obj in self.contents["ips"]:
                obj = resources.FloatingIP(obj, self.start, self.end)
                ips.append(obj)
            self._ips = ips
        return self._ips

    @property
    def volumes(self):
        if not self._volumes:
            objs = []
            for obj in self.contents["volumes"]:
                obj = resources.Volume(obj, self.start, self.end)
                objs.append(obj)
            self._volumes = objs
        return self._volumes

    def __iter__(self):
        return self

    def next(self):
        keys = self.contents.keys()
        for key in keys:
            yield key
        raise StopIteration()


class Resource(object):

    def __init__(self, resource, conn):
        self.resource = resource
        self.conn = conn
        self._meters = {}

    def meter(self, name, start, end):
        try:
            for meter in self.resource.links:
                if meter["rel"] == name:
                    m = Meter(self, meter["href"], self.conn, start, end, name)
                    self._meters[name] = m
                    return m
        except Exception as e:
            print "If you drop exceptions on the floor i will cut you."
            print e
        raise AttributeError("no such meter %s" % name)


class Meter(object):

    def __init__(self, resource, link, conn, start, end, name):
        self.resource = resource
        self.link = link.split('?')[0]  # strip off the resource_id crap.
        self.conn = conn
        self.start = start
        self.end = end
        self.name = name
        self.measurements = self.get_meter(start, end,
                                           self.conn.auth.auth_token)

    def get_meter(self, start, end, auth):
        # Meter is a href; in this case, it has a set of fields with it already.
        date_fields = add_dates(start - window_leadin, end)
        date_fields.append({'field': 'resource_id',
            'value': self.resource.resource.resource_id})

        r = requests.get(
            self.link,
            headers={
                "X-Auth-Token": auth,
                "Content-Type": "application/json"
            },
            data=json.dumps({'q': date_fields})
        )
        result = json.loads(r.text)
        return result

    def usage(self):
        return self.measurements
