import unittest
from artifice import interface
from artifice.interface import Artifice
import mock
import random
import json
from artifice.models.db_models import Tenant as tenant_model
from artifice.models.db_models import UsageEntry, Resource
# import copy

from sqlalchemy import create_engine
from artifice.models import Session

from datetime import datetime, timedelta

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


"""
This module tests interacting with the Ceilometer web service.
This will require an active Ceilometer with data in it, or,

"""

# @mock.patch("artifice.models.Session")
# @mock.patch("keystoneclient.v2_0.client.Client")
# @mock.patch("sqlalchemy.create_engine")
# def test_instance_artifice(self, sqlmock, keystone, session):

#     """Tests that artifice correctly instances."""
#     from artifice.interface import Artifice
#     # from artifice.models import usage

config = {
    "main": {
        "host_mapper": None
    },
    "database": {
        "username": "aurynn",
        "password": "aurynn",
        "host": "localhost",
        "port": "5433",
        "database": "artifice"
    },
    "openstack": {
        "username": "foo",
        "password": "bar",
        "default_tenant": "asdf",
        "authentication_url": "http://foo"
    },
    "ceilometer": {
        "host": 'http://whee'
    },
    "invoices": {
        "plugin": "json"
    }
}

# Enter in a whoooooole bunch of mock data.

TENANTS = [
    {u'enabled': True,
     u'description': None,
     u'name': u'demo',
     u'id': u'931dc699f9934021bb4a2b1088ba4d3b'}
]

DATACENTRE = "testcenter"


import os
try:
    fn = os.path.abspath(__file__)
    path, f = os.path.split(fn)
except NameError:
    path = os.getcwd()


fh = open(os.path.join(path, "data/resources.json"))
resources = json.loads(fh.read())
fh.close()

i = 0

mappings = {}

hosts = set([resource["metadata"]["host"] for resource
             in resources if resource["metadata"].get("host")])

while True:
    try:
        fh = open(os.path.join(path, "data/map_fixture_%s.json" % i))
        d = json.loads(fh.read())
        fh.close()
        mappings.update(d)
        i += 1
    except IOError:
        break

# Mappings should now be a set of resources.

AUTH_TOKEN = "ASDFTOKEN"

storages = []
vms = []
networks = []

# res = {"vms": [], "net": [], 'storage': [], "ports":[], "ips": []}
# res = {"vms": [], "network": [], 'storage': [], "ports":[]}
res = {"vms": [], "volumes": [], 'objects': [], "networks": [], "ips": []}


class InternalResource(object):

    def __init__(self, resource):
        self.resource = resource
    # def __getitem__(self, item):
    #     return self.resource[item]

    def __getattr__(self, attr):
        return self.resource[attr]

    def __str__(self):
        return str(self.resource)

    @property
    def links(self):
        return [MiniMeter(i) for i in self.resource['links']]


class MiniMeter(object):

    def __init__(self, meter):
        self._ = meter

    @property
    def link(self):
        return self._["href"]

    @property
    def rel(self):
        return self._["rel"]

    def __getitem__(self, item):
        return self._[item]


resources = [InternalResource(r) for r in resources]

for resource in resources:
    rels = [link.rel for link in resource.links if link.rel != 'self']
    if "image" in rels:
        continue
    elif "storage.objects.size" in rels:
        # Unknown how this data layout happens yet.
        # resource["_type"] = "storage"
        res["objects"].append(resource)
    elif "volume" in rels:
        res["volumes"].append(resource)
    elif "network.outgoing.bytes" in rels:
        res["networks"].append(resource)
    elif "state" in rels:
        res["vms"].append(resource)
    elif "ip.floating" in rels:
        res["ips"].append(resource)


def resources_replacement(tester):
    #
    def repl(self, start, end):
        tester.called_replacement_resources = True
        return resources


class TestInterface(unittest.TestCase):

    def setUp(self):

        engine = create_engine(os.environ["DATABASE_URL"])
        Session.configure(bind=engine)
        Base.metadata.create_all(engine)
        self.session = Session()
        self.objects = []
        self.session.rollback()
        self.called_replacement_resources = False

        self.resources = (res["networks"] + res["vms"] + res["objects"] +
                          res["volumes"] + res["ips"])

        self.start = datetime.now() - timedelta(days=30)
        self.end = datetime.now()

    def tearDown(self):

        self.session.query(UsageEntry).delete()
        self.session.query(tenant_model).delete()
        self.session.query(Resource).delete()
        self.session.commit()
        self.contents = None
        self.resources = []
        self.artifice = None
        self.usage = None

    @mock.patch("artifice.models.Session")
    # @mock.patch("artifice.interface.get_meter")
    # I don't think this will work
    @mock.patch("artifice.interface.keystone")
    @mock.patch("sqlalchemy.create_engine")
    def test_get_usage(self, sqlmock, keystone, session):

        # At this point, we prime the ceilometer/requests response
        # system, so that what we return to usage is what we expect
        # to get in the usage system.

        keystone.auth_token = AUTH_TOKEN
        # keystone.
        self.assertTrue(TENANTS is not None)

        def get_meter(self, start, end, auth):
            # Returns meter data from our data up above
            global mappings
            data = mappings[self.link]
            return data

        interface.get_meter = get_meter

        artifice = Artifice(config)
        self.artifice = artifice
        # Needed because this
        artifice.auth.tenants.list.return_value = TENANTS
        # this_config = copy.deepcopy(config["openstack"])
        # this_config["tenant_name"] = this_config["default_tenant"]
        # del this_config["default_tenant"]

        keystone.assert_called_with(
            username=config["openstack"]["username"],
            password=config["openstack"]["password"],
            tenant_name=config["openstack"]["default_tenant"],
            auth_url=config["openstack"]["authentication_url"]
        )
        tenants = None
        # try:
        tenants = artifice.tenants
        # except Exception as e:
        #     self.fail(e)

        # self.assertEqual ( len(tenants.vms), 1 )

        self.assertEqual(len(tenants), 1)
        k = tenants.keys()[0]
        t = tenants[k]  # First tenant
        self.assertTrue(isinstance(t, interface.Tenant))

        # t.resources = resources_replacement(self)
        # t.resources = mock.Mock(spec=interface.Resource)
        t.resources = mock.create_autospec(interface.Resource, spec_set=True)
        t.resources.return_value = self.resources

        try:
            hdc = getattr(artifice, "host_to_dc")
            self.assertTrue(callable(hdc))
        except AttributeError:
            self.fail("Artifice object lacks host_to_dc method ")

        # Replace the host_to_dc method with a mock that does what we need
        # it to do, for the purposes of testing.
        artifice.host_to_dc = mock.Mock()

        artifice.host_to_dc.return_value = DATACENTRE

        usage = t.usage(self.start, self.end)
        # try:

        # except Exception as e:
        #     self.fail(e)

        # self.assertTrue( self.called_replacement_resources )
        t.resources.assert_called_with(self.start, self.end)

        # So, we should be able to assert a couple of things here
        # What got called, when, and how.

        for call in artifice.host_to_dc.call_args_list:
            self.assertTrue(len(call[0]) == 1)
            self.assertTrue(call[0][0] in hosts)

        self.assertTrue(isinstance(usage, interface.Usage))

        # self.assertEqual( len(usage.vms), 1 )
        # self.assertEqual( len(usage.objects), 0)
        # self.assertEqual( len(usage.volumes), 0)

        # This is a fully qualified Usage object.
        self.usage = usage

    def add_element(self, from_):

        self.resources.append(res[from_][random.randrange(len(res[from_]))])

        self.test_get_usage()
        usage = self.usage

        # key = contents.keys()[0] # Key is the datacenter
        self.assertTrue(isinstance(usage, interface.Usage))

        try:
            getattr(usage, from_)
            # self.assertTrue( hasattr(usage, from_) )
        except AttributeError:
            self.fail("No property %s" % from_)

        try:
            getattr(usage, "vms")
        except AttributeError:
            self.fail("No property vms")

        lens = {"vms": 5}

        if from_ == "vms":
            lens["vms"] = 6
        else:
            lens[from_] = 2

        self.assertEqual(len(usage.vms), lens["vms"])
        self.assertEqual(len(getattr(usage, from_)), lens[from_])

        self.assertEqual(usage.vms[0].location, DATACENTRE)

    def test_add_instance(self):
        """
        Adds a new instance, tests that the returned data has both

        Tests that if we create a new instance in the data,
        we should get another instance in the returned contents.
        """

        self.add_element("vms")
        self.usage._vms = []
        self.assertTrue(len(self.usage.vms) == 6)

    def test_add_storage(self):

        self.add_element("objects")

    def test_correct_usage_values(self):
        """Usage data matches expected results:

        tests that we get the usage data we expect from the processing
        system as developed.

        """
        self.test_get_usage()

        usage = self.usage

        for vm in usage.vms:
            if vm.resource_id == "db8037b2-9f1c-4dd2-94dd-ea72f49a21d7":
                self.assertEqual(vm.uptime, 1)
            if vm.resource_id == "9a9e7c74-2a2f-4a30-bc75-fadcbc5f304a":
                self.assertEqual(vm.uptime, 1)
            if vm.resource_id == "0a57e3da-9e85-4690-8ba9-ee7573619ec3":
                self.assertEqual(vm.uptime, 1)
            if vm.resource_id == "de35c688-5a82-4ce5-a7e0-36245d2448bc":
                self.assertEqual(vm.uptime, 1)
            if vm.resource_id == "e404920f-cfc8-40ba-bc53-a5c610714bd9":
                self.assertEqual(vm.uptime, 0)
        for obj in usage.objects:
            if obj.resource_id == "3f7b702e4ca14cd99aebf4c4320e00ec":
                self.assertEqual(obj.size, 276189.372)
        for vol in usage.volumes:
            if vol.resource_id == "e788c617-01e9-405b-823f-803f44fb3483":
                self.assertEqual(vol.size, 0.045)
            if vol.resource_id == "6af83f4f-1f4f-40cf-810e-e3262dec718f":
                self.assertEqual(vol.size, 0.003)
        for net in usage.networks:
            if (net.resource_id ==
                    "nova-instance-instance-00000002-fa163ee2d5f6"):
                self.assertEqual(net.outgoing, 11.822)
                self.assertEqual(net.incoming, 9.734)
            if (net.resource_id ==
                    "nova-instance-instance-00000001-fa163edf2e3c"):
                self.assertEqual(net.outgoing, 6.306)
                self.assertEqual(net.incoming, 5.84)
            if (net.resource_id ==
                    "nova-instance-instance-00000005-fa163ee2fde1"):
                self.assertEqual(net.outgoing, 13.406)
                self.assertEqual(net.incoming, 10.795)
        for ip in usage.ips:
            if ip.resource_id == "84326068-5ccd-4a32-bcd2-c6c3af84d862":
                self.assertEqual(ip.duration, 1)
            if ip.resource_id == "2155db5c-4c7b-4787-90ff-7b8ded741c75":
                self.assertEqual(ip.duration, 1)
