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


class VM(object):

    def __init__(self, raw):
        # raw is the raw data for this
        self._raw = raw

        self._location = None

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
        return self._raw["metadata"]["memory"]

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


class Object(object):
    pass

class Volume(object):

    @property
    def location(self):
        pass
