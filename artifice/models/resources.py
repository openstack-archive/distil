from . import Base
from sqlalchemy import Column, String, types, schema, ForeignKey
from sqlalchemy.orm import relationship, backref
# from .tenants import Tenant
from decimal import *
import math


class Resource(Base):

    __tablename__ = "resources"

    id = Column(String, primary_key=True)
    type_ = Column(String)
    tenant_id = Column(String, ForeignKey("tenants.id"), primary_key=True)
    tenant = relationship("Tenant", backref=backref("tenants"))


class BaseModelConstruct(object):

    def __init__(self, raw, start, end):
        # raw is the raw data for this
        self._raw = raw
        self._location = None
        self.start = start
        self.end = end

    @property
    def amount(self):
        return self.size

    def __getitem__(self, item):
        return self._raw[item]

    def get(self, name):
        # Returns a given name value thing?
        # Based on patterning, this is expected to be a dict of usage
        # information based on a meter, I guess?
        return getattr(self, name)

    def _fetch_meter_name(self, name):
        return name

    def usage(self):
        dct = {}
        for meter in self.relevant_meters:
            meter = self._fetch_meter_name(meter)
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
            meter = self._fetch_meter_name(meter)
            try:
                self._raw.meter(meter, self.start, self.end).save()
            except AttributeError:
                # This is OK. We're not worried about non-existent meters,
                # I think. For now, anyway.
                pass


class VM(BaseModelConstruct):
    # The only relevant meters of interest are the type of the interest
    # and the amount of network we care about.
    # Oh, and floating IPs.
    relevant_meters = ["state"]

    usage_strategies = {"uptime": {"usage": "uptime", "rate": "flavor"}}

    type = "virtual_machine"

    def _fetch_meter_name(self, name):
        if name == "instance:<type>":
            return "instance:%s" % self.type
        return name

    @property
    def id(self):
        return self._raw.resource.resource_id

    @property
    def uptime(self):

        # this NEEDS to be moved to a config file or
        # possibly be queried from Clerk?
        tracked = [1, 2, 3, 6, 7]

        seconds = self.usage()['state'].uptime(tracked)

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
            return self._raw["metadata"]["flavor.name"]
        except KeyError:
            # print "\"instance_type\" was used"
            return self._raw["metadata"]["instance_type"]

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


class FloatingIP(BaseModelConstruct):

    relevant_meters = ["ip.floating"]

    usage_strategies = {"duration": {"usage": "duration", "rate": "type"}}

    type = "floating_ip"  # object storage

    @property
    def id(self):
        return self._raw.resource.resource_id

    @property
    def duration(self):
        # How much use this had.
        return Decimal(self.usage()["ip.floating"].volume())
        # Size is a gauge measured every 10 minutes.
        # So that needs to be compressed to 60-minute intervals


class Object(BaseModelConstruct):

    relevant_meters = ["storage.objects.size"]

    usage_strategies = {"size": {"usage": "size", "rate": "object_size"}}

    type = "object"  # object storage

    @property
    def id(self):
        return self._raw.resource.resource_id

    @property
    def size(self):
        # How much use this had.
        return Decimal(self.usage()["storage.objects.size"].volume())
        # Size is a gauge measured every 10 minutes.
        # So that needs to be compressed to 60-minute intervals


class Volume(BaseModelConstruct):

    relevant_meters = ["volume.size"]

    usage_strategies = {"size": {"usage": "size", "rate": "volume_size"}}

    type = "volume"

    @property
    def id(self):
        return self._raw.resource.resource_id

    @property
    def size(self):
        # Size of the thing over time.
        return Decimal(self.usage()["volume.size"].volume())


class Network(BaseModelConstruct):
    relevant_meters = ["network.outgoing.bytes", "network.incoming.bytes"]

    usage_strategies = {"outgoing": {"usage": "outgoing", "rate": "outgoing_bytes"},
                        "incoming": {"usage": "incoming", "rate": "incoming_bytes"}}

    type = "network"

    @property
    def id(self):
        return self._raw.resource.resource_id

    @property
    def outgoing(self):
        # Size of the thing over time.
        return Decimal(self.usage()["network.outgoing.bytes"].volume())

    @property
    def incoming(self):
        # Size of the thing over time.
        return Decimal(self.usage()["network.incoming.bytes"].volume())
