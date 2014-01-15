from . import Base
from sqlalchemy import Column, types, String


class Tenant(Base):

    __tablename__ = 'tenants'
    # ID is a uuid
    id = Column(String, primary_key=True, nullable=False)
    other_id = Column(String)
    # Some reference data to something else?
