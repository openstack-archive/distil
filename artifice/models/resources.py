from . import Base
from sqlalchemy import Column, types

class Resource(Base):

    __tablename__ = "resources"

    id = Column(String, primary_key=True)
    type_ = Column(String, primary_key=True)
    tenant_id = Column(String, ForeignKey("tenants.id"))
    tenant = relationship("Tenant", backref=backref("tenants", order_by="id"))