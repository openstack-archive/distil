# Interfaces to the Ceilometer API
import ceilometer

# Brings in HTTP support
import requests
import json

#
import datetime

# Provides authentication against Openstack
from keystoneclient.v2_0 import client

#
# from .models import usage
from .models import session, usage

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

class NotFound(BaseException): pass

class Artifice(object):
    """It's an artificer for making artifacts of billing!"""
    def __init__(self, config):
        super(Artifice, self).__init__()
        self.config = config

        # This is the Keystone client connection, which provides our
        # OpenStack authentication
        self.auth = client.Client(
            username=        config["openstack"]["username"],
            password=        config["openstack"]["password"],
            tenant_name=     config["openstack"]["default_tenant"],
            auth_url=        config["openstack"]["authenticator"]
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
        session.configure(bind=engine)
        self.artifice = None

    def tenant(self, name):
        """
        Returns a Tenant object describing the specified Tenant by name, or raises a NotFound error.
        """
        # Returns a Tenant object for the given name.
        # This is irritatingly inefficient
        self.config["authenticator"]
        url = "%(url)s/tenants?%(query)s" % {"url": self.config["authenticator"], "query": urllib.urlencode({"name":name})}
        r = requests.get(url, headers={"X-Auth-Token": keystone.auth_token, "Content-Type": "application/json"})
        if r.ok:
            data = json.loads(r.text)
            assert data
            t = Tenant(data["tenant"])
            return t
        else:
            if r.status_code == 404:
                # couldn't find it
                raise NotFound

    @property
    def tenants(self):
        """All the tenants in our system"""
        if not self._tenancy:
            self._tenancy = dict([(t.name, Tenant(t)) for t in self.auth.tenants.list()))
        return self._tenancy

class Tenant(object):

    def __init__(self, tenant):
        self.tenant = tenant
        # Conn is the niceometer object we were instanced from
        self.conn = None
        self._meters = set()
        self._resources = None

    def __getattr__(self, attr):
        if attr not in self.tenant:
            return super(self, Tenant).__getattr__(attr)
        return self.tenant["attr"]

    @property
    def resources(self):
        if not self._resources:
            r = requests.get(
                os.path.join(self.config["ceilometer"]["host"], "v2/resources"),
                headers={"X-Auth-Token": self.auth.auth_token, "Content-Type":"application/json"},
                data=json.dumps( { "q": resourcing_fields } )
            )
            if not r.ok:
                return None

            self._resources = json.loads(r.text)
        return self._resources

    def section(self, section):
        """returns an object-sort of thing to represent a section: VM or
           network or whatever"""
        return

    # def usage(self, start, end, section=None):
    def contents(self, start, end):
        # Returns a usage dict, based on regions.
        vms = {}
        vm_to_region = {}
        ports = {}

        usage_by_dc = {}

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
        ]
        writing_to = None

        vms = []
        networks = []
        storage = []
        images = []

        for resource in self.resources:
            rels = [link["rel"] for link in resource["links"] if link["rel"] != 'self' ]
            if "image" in rels:
                # Images don't have location data - we don't know where they are.
                # It may not matter where they are.
                resource["_type"] = "image"
                images.append(resource)
                pass
            elif "storage" in rels:
                # Unknown how this data layout happens yet.
                resource["_type"] = "storage"
                storage.append(resource)
                pass
            elif "network" in rels:
                # Have we seen the VM that owns this yet?
                resource["_type"] = "network"
                networks.append(resource)
            else:
                resource["_type"] = "vm"
                vms.append(resource)

        datacenters = {}
        region_tmpl = { "vms": [],
                    "network": [],
                    "storage": []
                }
        vm_to_region = {}
        for vm in vms:
            id_ = vm["resource_id"]

            datacenter = self.host_to_dc( vm["metadata"]["host"] )

            if datacenter not in datacenters:
                dict_ = copy(region_tmpl)
                datacenters[datacenter] = dict_

            datacenters[datacenter]["vms"].append(vm)

            vm_to_region[id_] = datacenter

        for network in networks:
            vm_id = network["metadata"]["instance_id"]
            datacenter = vm_to_region[ vm_id ]

            datacenters[datacenter]["network"].append(network)

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

        return Contents(datacenters, start, end)

    @property
    def meters(self):
        if not self.meters:
            resourcing_fields = [{"field": "project_id", "op": "eq", "value": self.tenant.id }]
            r = requests.get(
                os.path.join(self.config["ceilometer"]["host"], "v2/resources"),
                headers={"X-Auth-Token": self.auth.auth_token, "Content-Type":"application/json"},
                data=json.dumps( { "q": resourcing_fields } )
            )
            # meters = set()
            resources = json.loads(r.text)
            for resource in resources:
                for link in resource["links"]:
                    if link["rel"] == "self":
                        continue
                    self._meters.add(link["rel"])
                # sections.append(Section(self, link))
        return self._meters()


class Contents(object):

    def __init__(self, contents, start, end):
        self.contents = contents
        self.start = start
        self.end = end

        # Replaces all the internal references with better references to
        # actual metered values.
        self._replace()

    def __getitem__(self, item):

        return self.contents[item]

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
        for dc in contents.iterkeys():
            for section in contents[dc].iterkeys():
                meters = []
                for meter in contents[dc][section]:

                    usage = meter.usage(self.start, self.end)
                    usage.db = self.db # catch the DB context?

                    meters.append(usage)
                # Overwrite the original metering objects
                # with the core usage objects.
                # This is because we're not storing metering.
                contents[dc][section] = meters

    def save(self):

        """
        Iterate the list of things; save them to DB.
        """
        # self.db.begin()
        for dc in contents.iterkeys():
            for section in contents[dc].iterkeys():
                for meter in contents[dc][section]:
                    meter.save()
        self.db.commit()

class Resource(object):

    def __init__(self, resource):
        self.resource = resource

    @property
    def meters(self):
        meters = []
        for link in self.resource["links"]:
            if link["rel"] == "self":
                continue
            meter = Meter(self.resource, link)
            meters.append(meter)
        return meters

class Meter(object):

    def __init__(self, resource, link):
        self.resource = resource
        self.link = link
        # self.meter = meter

    def __getitem__(self, x):
        if isintance(x, slice):
            # Woo
            pass
        pass

    @property
    def usage(self, start, end):
        """
        Usage condenses the entirety of a meter into a single datapoint:
        A volume value that we can plot as a single number against previous
        usage for a given range.
        """
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
        r = requests.get(
            self.link,
            headers={
                "X-Auth-Token": self.auth.auth_token,
                "Content-Type":"application/json"},
            data=json.dumps({"q": date_fields})
        )
        measurements = json.loads(r)
        self.measurements = defaultdict(list)
        self.type = set([a["counter_type"] for a in measurements])
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
        # self.artifice.
        tenant_id = self.resource["tenant"]
        resource_id = self.resource["resource_id"]

        usage = models.Usage(
            resource_id,
            tenant_id,
            value,
            self.start,
            self.end,
        )
        self.db.add(usage)


    def volume(self):
        """
        Default billable number for this volume
        """
        return self.usage[-1]["counter_volume"]

class Cumulative(Artifact):

    def volume(self):
        measurements = self.usage
        measurements = sorted( measurements, key= lambda x: x["timestamp"] )
        total_usage = measurements[-1]["counter_volume"] - measurements[0]["counter_volume"]
        return total_usage

class Gauge(Artifact):

    # def volume(self):
    #   pass
    pass

class Delta(Artifact):

    pass
