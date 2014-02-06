from . import Base
from sqlalchemy import Column, types, String


class Tenant(Base):

    __tablename__ = 'tenants'
    # ID is a uuid
    tenant_id = Column(String, primary_key=True, nullable=False)
    name = Column(String)
    # Some reference data to something else?
