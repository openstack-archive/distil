from decimal import Decimal
import math

from artifice import constants


class BaseModelConstruct(object):

    def __init__(self, raw, start, end):
        # raw is the raw data for this
        self._raw = raw
        self._location = None
        self.start = start
        self.end = end

    @property
    def resource_id(self):
        return self._raw.resource.resource_id

    @property
    def tenant_id(self):
        return self._raw.resource.project_id

    @property
    def info(self):
        return {"type": self.type}

    def __getitem__(self, item):
        return self._raw[item]

    def get(self, name):
        # Returns a given name value thing?
        # Based on patterning, this is expected to be a dict of usage
        # information based on a meter, I guess?
        return getattr(self, name)

    def usage(self):
        dct = {}
        for meter in self.relevant_meters:
            try:
                vol = self._raw.meter(meter, self.start, self.end).volume()
                dct[meter] = vol
            except AttributeError:
                # This is OK. We're not worried about non-existent meters,
                # I think. For now, anyway.
                pass
        return dct

    def save(self):
        for meter in self.relevant_meters:
            try:
                self._raw.meter(meter, self.start, self.end).save()
            except AttributeError:
                # This is OK. We're not worried about non-existent meters,
                # I think. For now, anyway.
                pass


def to_mb(bytes):
    # function to make code easier to understand elsewhere.
    return (bytes / 1000) / 1000


class VM(BaseModelConstruct):
    # The only relevant meters of interest are the type of the interest
    # and the amount of network we care about.
    # Oh, and floating IPs.
    relevant_meters = ["state"]

    usage_strategies = {"uptime": {"usage": "uptime", "service": "flavor"}}

    type = "virtual_machine"

    @property
    def info(self):
        return {"name": self.name,
                "type": self.type}

    @property
    def uptime(self):

        # this NEEDS to be moved to a config file or
        # possibly be queried from Clerk?
        tracked_states = [constants.active, constants.building,
                          constants.paused, constants.rescued,
                          constants.resized]

        seconds = self.usage()["state"].uptime(tracked_states)

        # in hours, rounded up:
        uptime = math.ceil((seconds / 60.0) / 60.0)

        return Decimal(uptime)

    @property
    def flavor(self):
        # TODO FIgure out what the hell is going on with ceilometer here,
        # and why flavor.name isn't always there, and why
        # sometimes instance_type is needed instead....
        try:
            # print "\"flavor.name\" was used"
            return self._raw["metadata"]["flavor.name"].replace(".", "_")
        except KeyError:
            # print "\"instance_type\" was used"
            return self._raw["metadata"]["instance_type"].replace(".", "_")

    @property
    def memory(self):
        return self._raw["metadata"]["memory"]

    @property
    def cpus(self):
        return self._raw["metadata"]["vcpus"]

    @property
    def state(self):
        return self._raw["metadata"]["state"]

    @property
    def name(self):
        return self._raw["metadata"]["display_name"]

    @property
    def region(self):
        return self._raw["metadata"]["OS-EXT-AZ:availability_zone"]


class FloatingIP(BaseModelConstruct):

    relevant_meters = ["ip.floating"]

    usage_strategies = {"duration": {"usage": "duration", "service": "type"}}

    type = "floating_ip"  # object storage

    @property
    def duration(self):
        # How much use this had.
        return Decimal(self.usage()["ip.floating"].volume())
        # Size is a gauge measured every 10 minutes.
        # So that needs to be compressed to 60-minute intervals


class Object(BaseModelConstruct):

    relevant_meters = ["storage.objects.size"]

    usage_strategies = {"size": {"usage": "size", "service": "storage_size"}}

    type = "object_storage"  # object storage

    @property
    def size(self):
        # How much use this had.
        return Decimal(to_mb(self.usage()["storage.objects.size"].volume()))
        # Size is a gauge measured every 10 minutes.
        # So that needs to be compressed to 60-minute intervals


class Volume(BaseModelConstruct):

    relevant_meters = ["volume.size"]

    usage_strategies = {"size": {"usage": "size", "service": "volume_size"}}

    type = "volume"

    @property
    def info(self):
        return {"name": self.name,
                "type": self.type}

    @property
    def size(self):
        # Size of the thing over time.
        return Decimal(to_mb(self.usage()["volume.size"].volume()))

    @property
    def name(self):
        return self._raw["metadata"]["display_name"]


class Network(BaseModelConstruct):
    relevant_meters = ["network.outgoing.bytes", "network.incoming.bytes"]

    usage_strategies = {"outgoing": {"usage": "outgoing",
                                     "service": "outgoing_megabytes"},
                        "incoming": {"usage": "incoming",
                                     "service": "incoming_megabytes"}}

    type = "network_interface"

    @property
    def outgoing(self):
        # Size of the thing over time.
        return Decimal(to_mb(self.usage()["network.outgoing.bytes"].volume()))

    @property
    def incoming(self):
        # Size of the thing over time.
        return Decimal(to_mb(self.usage()["network.incoming.bytes"].volume()))
