from . import Base
from sqlalchemy import Column, types
from sqlalchemy.schema import CheckConstraint

class Tenant(Base):

    __tablename__ = 'tenants'
    # ID is a uuid
    id = Column(String, primary_key=True, nullable=False)
    # Some reference data to something else?