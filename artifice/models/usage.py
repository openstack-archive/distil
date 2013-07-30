from . import Base
from .resource import Resource
from sqlalchemy import Column, types
from sqlalchemy.orm import relationship, backref
# from sqlalchemy.schema import CheckConstraint
import datetime

from sqlalchemy.dialects.postgresql import ExcludeConstraint, TSRANGE


class Usage(Base):

    __tablename__ = 'usage'

    resource_id = Column(String, ForeignKey("resources.id"))
    resource =
    # tenant = Column(String, nullable=False)
    tenant_id = Column(String, ForeignKey("tenants.id"))
    tenant = relationship("Tenant", backref=backref("usage", order_by=created))
    volume = Column(String, nullable=False)
    time = Column(TSRANGE, nullable=False)
    start = Column(types.DateTime, nullable=False)
    end = Column(types.DateTime, nullable=False)
    created = Column(types.DateTime, nullable=False)

    __table_args__ = (
        ExcludeConstraint(
            ('tenant_id', '='),
            ('resource_id', '='),
            ('time', '&&')
        ),
        CheckConstraint("start > end"),
    )

    def __init__(self, resource, tenant, start, end):

        assert start < end

        self.time = [start, end]
        self.created = datetime.datetime.now()