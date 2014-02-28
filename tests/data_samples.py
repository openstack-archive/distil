import os
import json
import decimal


RESOURCES = {"vms": [], "volumes": [], 'objects': [],
             "networks": [], "ips": []}
MAPPINGS = {}
HOSTS = None


# The above variables are initialised beyond this point
try:
    fn = os.path.abspath(__file__)
    path, f = os.path.split(fn)
except NameError:
    path = os.getcwd()

# Enter in a whoooooole bunch of mock data.
fh = open(os.path.join(path, "data/resources.json"))
resources = json.loads(fh.read())
fh.close()

HOSTS = set([resource["metadata"]["host"] for resource
             in resources if resource["metadata"].get("host")])

i = 0
while True:
    try:
        fh = open(os.path.join(path, "data/map_fixture_%s.json" % i))
        d = json.loads(fh.read(), parse_float=decimal.Decimal)
        fh.close()
        MAPPINGS.update(d)
        i += 1
    except IOError:
        break


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
        RESOURCES["objects"].append(resource)
    elif "volume" in rels:
        RESOURCES["volumes"].append(resource)
    elif "network.outgoing.bytes" in rels:
        RESOURCES["networks"].append(resource)
    elif "state" in rels:
        RESOURCES["vms"].append(resource)
    elif "ip.floating" in rels:
        RESOURCES["ips"].append(resource)
