from . import Base
from sqlalchemy import Column, Text, DateTime, Float, Boolean


class UsageEntry(Base):
    __tablename__ = 'usage'
    service = Column(Text, primary_key=True)
    volume = Column(Float)
    resource_id = Column(Text, primary_key=True)
    tenant_id = Column(Text, primary_key=True)
    start = Column(DateTime)
    end = Column(DateTime, primary_key=True)


class Resource(Base):
    __tablename__ = 'resources'
    resource_id = Column(Text, primary_key=True)
    info = Column(Text)


class SalesOrder(Base):
    __tablename__ = 'sales_orders'
    tenant_id = Column(Text, primary_key=True)
    start = Column(DateTime)
    end = Column(DateTime, primary_key=True)


class Tenant(Base):

    __tablename__ = 'tenants'
    # ID is a uuid
    tenant_id = Column(Text, primary_key=True, nullable=False)
    name = Column(Text)
    info = Column(Text)
    active = Column(Boolean, default=True)
    # Some reference data to something else?
