from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import Column, Text, DateTime, Boolean, DECIMAL
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method

from sqlalchemy import select, func, and_

Base = declarative_base()
#
Session = sessionmaker()
# 
# class Tenant(Base):
#     
#     id = Column(text, primary_key=True)
#     active = Column(Boolean, default=True)
# 
#     usage = relationship(Usage, backref="owner")
#     resources = relationship(Resources, backref="owner")
#     
#     @hybrid_method
#     def usage(self, start, end):
#         pass
# 
#     @usage.expression
#     def usage(cls, start, end):
#         return select([func.sum(Usage.volume)]).\
#                 where(
#                     and_( Usage.tenant == cls.id,
#                           Usage.intersects(start, end)
#                         )
#                 ).\
#                 label('total_usage') 


class UsageEntry(Base):
    """Simplified data store of usage information for a given service,
       in a resource, in a tenant. Similar to ceilometer datastore,
       but stores local transformed data."""
    __tablename__ = 'usage'

    # Service is things like incoming vs. outgoing, as well as instance
    # flavour
    service = Column(Text, primary_key=True)
    volume = Column(DECIMAL, nullable=False)
    resource_id = Column(Text, primary_key=True)
    tenant_id = Column(Text, primary_key=True)
    start = Column(DateTime)
    end = Column(DateTime, primary_key=True)

class Resource(Base):
    """Database model for storing metadata associated with a resource."""
    __tablename__ = 'resources'
    resource_id = Column(Text, primary_key=True)
    tenant_id = Column(Text, primary_key=True)
    info = Column(Text)


# this might not be a needed model?
class SalesOrder(Base):
    """Historic billing periods so that tenants cannot be rebuild accidentally."""
    __tablename__ = 'sales_orders'
    tenant_id = Column(Text, primary_key=True)
    start = Column(DateTime)
    end = Column(DateTime, primary_key=True)


class Tenant(Base):
    """Model for storage of metadata related to a tenant."""
    __tablename__ = 'tenants'
    # ID is a uuid
    tenant_id = Column(Text, primary_key=True, nullable=False)
    name = Column(Text)
    info = Column(Text)
    active = Column(Boolean, default=True)
    # Some reference data to something else?
