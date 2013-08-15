# Interfaces to the Ceilometer API
# import ceilometer

# Brings in HTTP support
import requests
import json


from copy import copy
from collections import defaultdict

#
import datetime

# Provides authentication against Openstack
from keystoneclient.v2_0 import client as KeystoneClient

# Provides hooks to ceilometer, which we need for data.
from ceilometerclient.v2.client import Client as ceilometer

# from .models import usage
from .models import Session, usage

from sqlalchemy import create_engine

from .models.usage import Usage
from .models import resources, tenants

# from .models.tenants import Tenant

# Date format Ceilometer uses
# 2013-07-03T13:34:17
# which is, as an strftime:
# timestamp = datetime.strptime(res["timestamp"], "%Y-%m-%dT%H:%M:%S.%f")
# or
# timestamp = datetime.strptime(res["timestamp"], "%Y-%m-%dT%H:%M:%S")

# Most of the time we use date_format
date_format = "%Y-%m-%dT%H:%M:%S"
# Sometimes things also have milliseconds, so we look for that too.
other_date_format = "%Y-%m-%dT%H:%M:%S.%f"

def get_meter(meter, start, end, auth):
    date_fields = [{
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
    # I dislike directly calling requests here.
    r = requests.get(
        meter.link,
        headers={
            "X-Auth-Token": auth,
            "Content-Type":"application/json"},
        data=json.dumps({"q": date_fields})
    )
    return json.loads(r)


class NotFound(BaseException): pass

class keystone(KeystoneClient.Client):

    def tenant_by_name(self, name):
        authenticator = self.auth_url
        url = "%(url)s/tenants?%(query)s" % {
            "url": authenticator,
            "query": urllib.urlencode({"name":name})
            }
        r = requests.get(url, headers={
            "X-Auth-Token": self.auth_token,
            "Content-Type": "application/json"
        })
        if r.ok:
            data = json.loads(r.text)
            assert data
            return data
        else:
            if r.status_code == 404:
                # couldn't find it
                raise NotFound

class Artifice(object):
    """Produces billable artifacts"""
    def __init__(self, config):
        super(Artifice, self).__init__()
        self.config = config

        # This is the Keystone client connection, which provides our
        # OpenStack authentication
        self.auth = keystone(
            username=        config["openstack"]["username"],
            password=        config["openstack"]["password"],
            tenant_name=     config["openstack"]["default_tenant"],
            auth_url=        config["openstack"]["authentication_url"]
            # auth_url="http://localhost:35357/v2.0"
        )
        conn_string = 'postgresql://%(username)s:%(password)s@%(host)s:%(port)s/%(database)s' % {
            "username": config["database"]["username"],
            "password": config["database"]["password"],
            "host":     config["database"]["host"],
            "port":     config["database"]["port"],
            "database": config["database"]["database"]
        }
        engine = create_engine(conn_string)
        Session.configure(bind=engine)
        self.session = Session()
        self.artifice = None

        self.ceilometer = ceilometer(
            self.config["ceilometer"]["host"],
            token=self.auth.auth_token
        )
        self._tenancy = None


    def tenant(self, name):
        """
        Returns a Tenant object describing the specified Tenant by name, or raises a NotFound error.
        """
        # Returns a Tenant object for the given name.
        # Uses Keystone API to perform a direct name lookup,
        # as this is expected to work via name.

        data = self.auth.tenant_by_name(name)
        t = Tenant(data["tenant"], self)
        return t

    @property
    def tenants(self):
        """All the tenants in our system"""
        # print "tenant list is %s" % self.auth.tenants.list()
        if not self._tenancy:
            self._tenancy = {}
            invoice_type = __import__(self.config["invoices"]["plugin"])
            for tenant in self.auth.tenants.list():
                t = Tenant(tenant, self)
                self._tenancy[t.name] = t
        return self._tenancy

class Tenant(object):

    def __init__(self, tenant, conn):
        self.tenant = tenant
        # Conn is the niceometer object we were instanced from
        self.conn = conn
        self._meters = set()
        self._resources = None
        self.invoice_type = None

        # Invoice type needs to get set from the config, which is
        # part of the Artifice setup above.


    def __getattr__(self, attr):
        if attr not in self.tenant:
            return object.__getattribute__(self, attr)
            # return super(Tenant, self).__getattr__(attr)
        return self.tenant[attr]


    def invoice(self):

        """
        Creates a new Invoice.
        Invoices are an Artifice datamodel that represent a
        set of billable entries assigned to a client on a given Date.
        An Invoice offers very little of its own opinions,
        requiring a backend plugin to operate.
        @returns: invoice
        """

        if self.invoice_type is None:
            invoice_type = self.conn.config["main"]["invoice:object"]
            if ":" not in invoice_type:
                raise AttributeError("Invoice configuration incorrect! %s" % invoice_type)
            module, call = invoice_type.split(":")
            _package = __import__(module, globals(), locals(), [call])
            funct = getattr(_package, call)
            self.invoice_type = funct
        # Change from ConfigParser format into a straight dict
        config = dict(self.conn.config.items("invoice_object"))
        invoice = self.invoice_type(self, config)
        return invoice

    def resources(self, start, end):
        if not self._resources:
            date_fields = [{
                "field": "timestamp",
                    "op": "ge",
                    "value": start.strftime(date_format)
                },
                {
                    "field": "timestamp",
                    "op": "lt",
                    "value": end.strftime(date_format)
                },
                {   "field": "project_id",
                    "op": "eq",
                    "value": self.tenant["id"]
                },
            ]
            self._resources = self.ceilometer.resources.list(date_fields)
        return self._resources

    # def usage(self, start, end, section=None):
    def usage(self, start, end):
        """
        Contents is the meat of Artifice, returning a dict of location to
        sub-information
        """
        # Returns a usage dict, based on regions.
        vms = {}
        vm_to_region = {}
        ports = {}

        usage_by_dc = {}

        writing_to = None

        vms = []
        networks = []
        storage = []
        images = []
        volumes = []

        for resource in self.resources(start, end):
            rels = [link["rel"] for link in resource["links"] if link["rel"] != 'self' ]
            if "image" in rels:
                # Images don't have location data - we don't know where they are.
                # It may not matter where they are.
                resource["_type"] = "image"
                images.append(Resource(resource, self.conn))
                pass
            elif "storage.objects" in rels:
                # Unknown how this data layout happens yet.
                resource["_type"] = "object"
                storage.append(Resource(resource, self.conn))
                pass
            elif "network" in rels:
                # Have we seen the VM that owns this yet?
                resource["_type"] = "network"
                networks.append(Resource(resource , self.conn))
            elif "volumne" in rels:
                volumes.append( Resource(resource, self.conn) )
            elif 'instance' in rels:
                resource["_type"] = "vm"
                vms.append(Resource(resource, self.conn ))

        datacenters = {}
        region_tmpl = { "vms": vms,
                    "network": networks,
                    "objects": storage,
                    "volumes": volumes

                }
        # vm_to_region = {}
        # for vm in vms:
        #     id_ = vm["resource_id"]

        #     datacenter = self.conn.host_to_dc( vm["metadata"]["host"] )

        #     if datacenter not in datacenters:
        #         dict_ = copy(region_tmpl)
        #         datacenters[datacenter] = dict_

        #     datacenters[datacenter]["vms"].append(vm)

        #     vm_to_region[id_] = datacenter

        # for network in networks:
        #     vm_id = network["metadata"]["instance_id"]
        #     datacenter = self.host_to_dc( network["metadata"]["host"] )

        #     datacenters[datacenter]["network"].append(network)

        # for resource in storage:
        #   pass

        # for image in images:
        #   pass
        #   # These can be billed as internal transfer, or block storage. TBD.

        # Now, we have everything arranged by region
        # As we've not queried for individual meters as yet, this represents
        # only the breakdown of resources that exist in the various datacenter/region
        # constructs.
        # So we can now start to collect stats and construct what we consider to be
        # usage information for this tenant for this timerange

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


        # Replaces all the internal references with better references to
        # actual metered values.
        # self._replace()

    @property
    def vms(self):

        if not self._vms:
            vms = []

            for vm in self.contents["vms"]:
                VM = resources.VM(vm)
                VM.location = self.conn.host_to_dc( vm["metadata"]["host"] )
                vms.append(VM)
            self._vms = vms
        return self._vms

    @property
    def objects(self):
        if not self._objects:
            vms = []

            for object_ in self.contents["objects"]:
                obj = resources.Object(object_)
                obj.location = self.conn.host_to_dc( vm["metadata"]["host"] )
                vms.append(VM)
            self._vms = vms
        return self._vms

    @property
    def volumes(self):
        return []

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

    def _replace(self):
        # Turns individual metering objects into
        # Usage objects that this expects.
        for dc in self.contents.iterkeys():
            for section in self.contents[dc].iterkeys():
                meters = []
                for resource in self.contents[dc][section]:
                    meters.extend(resource.meters)
                usages = []
                for meter in meters:
                    usage = meter.usage(self.start, self.end)
                    usage.db = self.conn # catch the DB context?

                    usages.append(usage)
                # Overwrite the original metering objects
                # with the core usage objects.
                # This is because we're not storing metering.
                self.contents[dc][section] = usages

    def save(self):

        """
        Iterate the list of things; save them to DB.
        """
        # self.db.begin()
        # for
        # for dc in self.contents.iterkeys():
        #     for section in self.contents[dc].iterkeys():
        #         for meter in self.contents[dc][section]:
        #             meter.save()
        # self.conn.session.commit()
        raise NotImplementedError("Not implemented")

class Resource(object):

    def __init__(self, resource, conn):
        self.resource = resource
        self.conn = conn
        self._meters = {}

    def meter(self, name):
        pass # Return a named meter


    def __getitem__(self, name):
        return self.resource[name]

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

    def __init__(self, resource, link, conn):
        self.resource = resource
        self.link = link
        self.conn = conn
        # self.meter = meter

    def __getitem__(self, x):
        if isinstance(x, slice):
            # Woo
            pass
        pass

    def usage(self, start, end):
        """
        Usage condenses the entirety of a meter into a single datapoint:
        A volume value that we can plot as a single number against previous
        usage for a given range.
        """
        measurements = get_meter(self, start, end, self.conn.auth.auth_token)

        self.measurements = defaultdict(list)
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
            # The usage is the last one, which is the highest value.
            #
            # Base it just on the resource ID.
            # Is this a reasonable thing to do?
            # Composition style: resource.meter("cpu_util").usage(start, end) == artifact
            type_ = Cumulative
        elif self.type == "gauge":
            type_ = Gauge
            # return Gauge(self.Resource, )
        elif self.type == "delta":
            type_ = Delta

        return type_(self.resource, measurements, start, end)

class Artifact(object):

    """
    Provides base artifact controls; generic typing information
    for the artifact structures.
    """

    def __init__(self, resource, usage, start, end):

        self.resource = resource
        self.usage = usage
        self.start = start
        self.end = end

    def __getitem__(self, item):
        if item in self._data:
            return self._data[item]
        raise KeyError("no such item %s" % item)

    def save(self):
        """
        Persists to our database backend. Opinionatedly this is a sql datastore.
        """
        value = self.volume()
        session = self.resource.conn.session
        # self.artifice.
        try:
            tenant_id = self.resource["tenant_id"]
        except KeyError:
            tenant_id = self.resource["project_id"]
        resource_id = self.resource["resource_id"]

        tenant = session.query(tenants.Tenant).get(tenant_id)

        if tenant is None:
            res = resources.Resource()
            tenant = tenants.Tenant()
            tenant.id = tenant_id

            res.id = resource_id
            res.tenant = tenant
            session.add(res)
            session.add(tenant)
        else:
            try:
                res = session.query(resources.Resource).filter(resources.Resource.id == resource_id)[0]
                tenant = res.tenant
            except IndexError:
                res = resources.Resource()
                tenant = tenants.Tenant()
                tenant.id = tenant_id
                res.id = resource_id
                res.tenant = tenant
                session.add(res)
                session.add(tenant)

        usage = Usage(
            res,
            tenant,
            value,
            self.start,
            self.end,
        )
        session.add(usage)
        session.commit() # Persist to our backend


    def volume(self):
        """
        Default billable number for this volume
        """
        return sum([x["counter_volume"] for x in self.usage])

class Cumulative(Artifact):

    def volume(self):
        measurements = self.usage
        measurements = sorted( measurements, key= lambda x: x["timestamp"] )
        total_usage = measurements[-1]["counter_volume"] - measurements[0]["counter_volume"]
        return total_usage


# Gauge and Delta have very little to do: They are expected only to
# exist as "not a cumulative" sort of artifact.
class Gauge(Artifact):
    pass

class Delta(Artifact):
    pass
