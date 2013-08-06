from . import Base
from .resources import Resource
from sqlalchemy import Column, types, ForeignKey, CheckConstraint, String
from sqlalchemy.orm import relationship, backref
# from sqlalchemy.schema import CheckConstraint
import datetime

from sqlalchemy.dialects.postgresql import ExcludeConstraint, TSRANGE


class Usage(Base):

    __tablename__ = 'usage'

    resource_id = Column(String, ForeignKey("resources.id"), primary_key=True)
    # tenant = Column(String, nullable=False)
    tenant_id = Column(String, ForeignKey("tenants.id"), primary_key=True)

    volume = Column(String, nullable=False)
    time = Column(TSRANGE, nullable=False)
    created = Column(types.DateTime, nullable=False)

    resource = relationship("Resource", backref=backref("resources", order_by=created))
    tenant = relationship("Tenant", backref=backref("usage", order_by=created))

    __table_args__ = (
        ExcludeConstraint(
            ('tenant_id', '='),
            ('resource_id', '='),
            ('time', '&&')
        ),
    )

    def __init__(self, resource, tenant, value, start, end):

        assert start < end

        self.resource_id = resource
        self.tenant_id = tenant
        self.time = [start, end]
        self.created = datetime.datetime.now()
        self.volume = value