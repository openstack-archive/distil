import unittest
from artifice import interface
from artifice.interface import Artifice
import mock
import random
import json
import copy

from sqlalchemy import create_engine
from artifice.models import Session
from artifice.models import usage, tenants
from artifice.models.resources import Resource

from datetime import datetime, timedelta


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
    "main": {},
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
        "default_tenant":"asdf",
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


# I think three is good
import os
try:
    fn = os.path.abspath(__file__)
    path, f = os.path.split(fn)
except NameError:
    path = os.getcwd()


fh = open( os.path.join( path, "data/resources.json") )
resources = json.loads(fh.read () )
fh.close()

i = 0

mappings = {}

hosts = set([resource["metadata"]["host"] for resource in resources if resource["metadata"].get("host")])

while True:
    try:
        fh = open(  os.path.join( path, "data/map_fixture_%s.json" % i ) )
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
res = {"vms": [], "volumes": [], 'objects': [], "network": []}

for resource in resources:
    rels = [link["rel"] for link in resource["links"] if link["rel"] != 'self' ]
    if "image" in rels:
        continue
    elif "storage.objects" in rels:
        # Unknown how this data layout happens yet.
        # resource["_type"] = "storage"
        res["objects"].append(resource)
    elif "volume" in rels:
        res["volumes"].append(resource)
    elif "network" in rels:
        res["network"].append(resource)
    elif "instance" in rels:
        res["vms"].append(resource)
    # elif "port" in rels:
    #     res["ports"].append(resource)
    # elif "ip.floating" in rels:
    #     res["ips"].append(resource)

def resources_replacement(tester):
    #
    def repl(self, start, end):
        tester.called_replacement_resources = True
        return resources

class TestInterface(unittest.TestCase):

    def setUp(self):

        engine = create_engine(os.environ["DATABASE_URL"])
        Session.configure(bind=engine)
        self.session = Session()
        self.objects = []
        self.session.rollback()
        self.called_replacement_resources = False

        num = random.randrange(len(res["vms"]))
        # Only one vm for this
        self.resources = [ res["vms"][ num ] ]

        self.start = datetime.now() - timedelta(days=30)
        self.end = datetime.now()

    def tearDown(self):

        self.session.query(usage.Usage).delete()
        self.session.query(Resource).delete()
        self.session.query(tenants.Tenant).delete()

        self.session.commit()
        self.contents = None
        self.resources = []
        self.artifice = None


    @mock.patch("artifice.models.Session")
    # @mock.patch("artifice.interface.get_meter") # I don't think this will work
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
            # print self.link
            data = mappings[self.link["href"]]
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
            username=        config["openstack"]["username"],
            password=        config["openstack"]["password"],
            tenant_name=     config["openstack"]["default_tenant"],
            auth_url=        config["openstack"]["authentication_url"]
        )
        tenants = None
        try:
            tenants = artifice.tenants
        except Exception as e:
            self.fail(e)

        # self.assertEqual ( len(tenants.vms), 1 )

        self.assertEqual( len(tenants), 1 )
        k = tenants.keys()[0]
        t = tenants[k]
        self.assertTrue( isinstance( t, interface.Tenant ) )

        contents = None

        # t.resources = resources_replacement(self)
        t.resources = mock.Mock()
        t.resources.return_value = self.resources

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
            self.assertTrue ( len(call[0]) == 1 )
            self.assertTrue ( call[0][0] in hosts )

        self.assertTrue ( isinstance(usage, interface.Usage) )

        # self.assertEqual( len(usage.vms), 1 )
        # self.assertEqual( len(usage.objects), 0)
        # self.assertEqual( len(usage.volumes), 0)

        self.usage = usage

    # @mock.patch("artifice.models.Session")
    # @mock.patch("artifice.interface.get_meter") # I don't think this will work
    # @mock.patch("artifice.interface.keystone")
    # @mock.patch("sqlalchemy.create_engine")
    # def test_save_smaller_range_no_overlap(self, sqlmock, keystone, meters, session):

    #     self.test_get_usage()

    #     first_contents = self.usage

    #     # self.resources = [
    #     #     res["vms"][random.randrange(len[res["vms"]])],
    #     # ]


    def add_element(self, from_):

        self.resources.append( res[from_][random.randrange(len(res[from_]))] )
        print len(self.resources)

        self.test_get_usage()
        usage = self.usage

        # key = contents.keys()[0] # Key is the datacenter
        print from_

        self.assertTrue( isinstance(usage, interface.Usage) )

        try:
            getattr(usage, from_)
            # self.assertTrue( hasattr(usage, from_) )
        except AttributeError:
            self.fail("No property %s" % from_)

        try:
            getattr(usage, "vms")
        except AttributeError:
            self.fail ("No property vms")

        lens = { "vms": 1 }

        if from_ == "vms":
            lens["vms"] = 2
        else:
            lens[from_] = 1

        self.assertEqual(len(usage.vms), lens["vms"])
        self.assertEqual(len( getattr(usage, from_) ), lens[from_])

        self.assertEqual( usage.vms[0].location, DATACENTRE )

    def test_add_instance(self):
        """
        Adds a new instance, tests that the returned data has both

        Tests that if we create a new instance in the data,
        we should get another instance in the returned contents.
        """

        self.add_element("vms")

    def test_add_storage(self):

        self.add_element("objects")

    # def test_add_ip(self):
    #     self.add_element("ips")

    def test_save_contents(self):

        self.test_get_usage()

        usage = self.usage
        # try:
        usage.save()
        # except Exception as e:

        # Now examine the database

    def test_correct_usage_values(self):
        """Usage data matches expected results:

        tests that we get the usage data we expect from the processing
        system as developed.

        """
        self.test_get_usage()

        usage = self.usage

        for vm in usage.vms:
            volume = vm.usage()
            # print "vm is %s" % vm
            # print vm.size
            # print "Volume is: %s" % volume
            # VM here is a resource object, not an underlying meter object.
            id_ = vm["project_id"]

            for rvm in self.resources:
                if not rvm["project_id"] == id_:
                    continue
                for meter in rvm["links"]:
                    if not meter["rel"] in volume:
                        continue
                    data = mappings[ meter["href"] ]
                    vol = volume[ meter["rel"] ]

                    type_ = data[0]["counter_type"]
                    if type_ == "cumulative":
                        v = interface.Cumulative(rvm, data, self.start, self.end)
                    elif type_ == "gauge":
                        v = interface.Gauge(rvm, data, self.start, self.end)
                    elif type_ == "delta":
                        v = interface.Delta(rvm, data, self.start, self.end)
                    # Same type of data
                    self.assertEqual( v.__class__, vol.__class__ )
                    self.assertEqual( v.volume(), vol.volume() )


    def test_use_a_bunch_of_data(self):
        pass
