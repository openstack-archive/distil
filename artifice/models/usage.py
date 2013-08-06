from . import Base
from .resources import Resource
from sqlalchemy import Column, types, ForeignKey, CheckConstraint, String, Integer, type_coerce, func, Sequence
from sqlalchemy.orm import relationship, backref
# from sqlalchemy.schema import CheckConstraint
import datetime

from sqlalchemy.dialects.postgresql import ExcludeConstraint, TSRANGE, ARRAY

class TSRange(TSRANGE):

    def bind_expression(self, bindvalue):
        # convert the bind's type from PGPString to
        # String, so that it's passed to psycopg2 as is without
        # a dbapi.Binary wrapper
        # raise Exception("asdf")
        bindvalue = type_coerce(bindvalue, String)
        return func.tsrange(bindvalue)
        # return "'%s::tsrange'" % bindvalue


class Usage(Base):

    __tablename__ = 'usage'

    id_ = Column(Integer, Sequence('usage_id_seq'), primary_key=True)
    resource_id = Column(String, ForeignKey("resources.id"))
    # tenant = Column(String, nullable=False)
    tenant_id = Column(String, ForeignKey("tenants.id"))

    volume = Column(String, nullable=False)
    time = Column(TSRange, nullable=False)
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
        assert isinstance(start, datetime.datetime)
        assert isinstance(end, datetime.datetime)

        self.resource = resource
        self.tenant = tenant
        self.time = "[%s,%s]" % (start, end)
        self.created = datetime.datetime.now()
        self.volume = value