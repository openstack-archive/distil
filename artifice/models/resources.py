from . import Base
from sqlalchemy import Column, String, types, schema, ForeignKey
from sqlalchemy.orm import relationship, backref
from .tenants import Tenant

class Resource(Base):

    __tablename__ = "resources"

    id = Column(String, primary_key=True)
    type_ = Column(String)
    tenant_id = Column(String, ForeignKey("tenants.id"))
    tenant = relationship("Tenant", backref=backref("tenants", order_by=Tenant.id))