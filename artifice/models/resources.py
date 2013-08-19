from . import Base
from sqlalchemy import Column, String, types, schema, ForeignKey
from sqlalchemy.orm import relationship, backref
# from .tenants import Tenant

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

    def __getitem__(self, item):
        return self._raw[item]

    def _fetch_meter_name(self, name):
        return name

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

    relevant_meters = ["instance:<type>", "network.incoming.bytes", "network.outgoing.bytes"]

    def _fetch_meter_name(self, name):
        if name == "instance:<type>":
            return "instance:%s" % self.type
        return name

    @property
    def type(self):
        return self._raw["metadata"]["instance_type"]

    @property
    def size(self):
        return self.type

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
    def bandwidth(self):
        # This is a metered value
        return 0

    @property
    def ips(self):
        """floating IPs; this is a metered value"""
        return 0


class Object(BaseModelConstruct):

    relevant_meters = ["storage.objects.size"]

    def __init__(self, raw, start, end):
        self._obj = raw
        self.start, self.end = start, end

    @property
    def size(self):
        # How much use this had.
        meter = self._raw.meter("storage.objects.size")
        usage = meter.usage(self.start, self.end)

        return usage.volume()

        # Size is a gauge measured every 10 minutes.
        # So that needs to be compressed to 60-minute intervals



class Volume(BaseModelConstruct):

    relevant_meters = ["volume.size"]

    @property
    def location(self):
        pass

    def size(self):
        # Size of the thing over time.
        return self._raw.meter("volume.size", self.start, self.end).volume()

