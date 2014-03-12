import requests
import json
from collections import defaultdict
import artifact
import auth
from ceilometerclient.v2.client import Client as ceilometer
from .models import resources
from constants import date_format


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
    def __init__(self, config):
        super(Artifice, self).__init__()
        self.config = config

        # This is the Keystone client connection, which provides our
        # OpenStack authentication
        self.auth = auth.Keystone(
            username=config["openstack"]["username"],
            password=config["openstack"]["password"],
            tenant_name=config["openstack"]["default_tenant"],
            auth_url=config["openstack"]["authentication_url"]
        )

        self.ceilometer = ceilometer(
            self.config["ceilometer"]["host"],
            # Uses a lambda as ceilometer apparently wants
            # to use it as a callable?
            token=lambda: self.auth.auth_token
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

    def __getitem__(self, item):

        try:
            return getattr(self.tenant, item)
        except AttributeError:
            try:
                return self.tenant[item]
            except KeyError:
                raise KeyError("No such key '%s' in tenant" % item)

    def __getattr__(self, attr):
        if attr not in self.tenant:
            return object.__getattribute__(self, attr)
        return self.tenant[attr]

    def resources(self, start, end):
        if not self._resources:

            date_fields = [
                {"field": "project_id",
                 "op": "eq",
                 "value": self.tenant["id"]
                 },
            ]
            date_fields.extend(add_dates(start, end))
            # Sets up our resources as Ceilometer objects.
            # That's cool, I think.
            self._resources = self.conn.ceilometer.resources.list(date_fields)
        return self._resources

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
    # def __getitem__(self, item):

    #     return self.contents[item]

    def __iter__(self):
        return self

    def next(self):
        # pass
        keys = self.contents.keys()
        for key in keys:
            yield key
        raise StopIteration()


class Resource(object):

    def __init__(self, resource, conn):
        self.resource = resource
        self.conn = conn
        self._meters = {}

    # def __getitem__(self, item):
    #     return self.resource

    def meter(self, name, start, end):
        pass  # Return a named meter
        for meter in self.resource.links:
            if meter["rel"] == name:
                m = Meter(self, meter["href"], self.conn, start, end)
                self._meters[name] = m
                return m
        raise AttributeError("no such meter %s" % name)

    def __getitem__(self, name):
        # print name
        # print self.resource
        # print self.resource[name]
        return getattr(self.resource, name)
        # return self.resource.name

    @property
    def meters(self):
        if not self._meters:
            meters = []
            for link in self.resource["links"]:
                if link["rel"] == "self":
                    continue
                meter = Meter(self, link, self.conn)
                meters.append(meter)
            self._meters = meters
        return self._meters


class Meter(object):

    def __init__(self, resource, link, conn, start=None, end=None):
        self.resource = resource
        self.link = link
        self.conn = conn
        self.start = start
        self.end = end
        # self.meter = meter

    def get_meter(self, start, end, auth):
        # Meter is a href; in this case, it has a set of fields with it already.
        date_fields = add_dates(start, end)
        fields = []
        for field in date_fields:
            fields.append(("q.field", field["field"]))
            fields.append(("q.op", field["op"]))
            fields.append(("q.value", field["value"]))

        r = requests.get(
            self.link,
            headers={
                "X-Auth-Token": auth,
                "Content-Type": "application/json"}
        )
        return json.loads(r.text)

    def volume(self):
        return self.usage(self.start, self.end)

    def usage(self, start, end):
        """
        Usage condenses the entirety of a meter into a single datapoint:
        A volume value that we can plot as a single number against previous
        usage for a given range.
        """
        measurements = self.get_meter(start, end, self.conn.auth.auth_token)
        # return measurements

        # print measurements

        # self.measurements = defaultdict(list)
        self.type = set([a["counter_type"] for a in measurements])
        if len(self.type) > 1:
            # That's a big problem
            raise RuntimeError("Too many types for measurement!")
        elif len(self.type) == 0:
            raise RuntimeError("No types!")
        else:
            self.type = self.type.pop()
        type_ = None
        if self.type == "cumulative":
            type_ = artifact.Cumulative
        elif self.type == "gauge":
            type_ = artifact.Gauge
        elif self.type == "delta":
            type_ = artifact.Delta

        return type_(self.resource, measurements, start, end)
