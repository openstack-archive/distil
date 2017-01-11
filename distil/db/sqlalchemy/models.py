# Copyright (C) 2014 Catalyst IT Ltd
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from sqlalchemy import Column
from sqlalchemy import Integer
from sqlalchemy import DateTime
from sqlalchemy import ForeignKey
from sqlalchemy import ForeignKeyConstraint
from sqlalchemy import Numeric
from sqlalchemy import Sequence
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.orm import relationship

from distil.db.sqlalchemy.model_base import JSONEncodedDict
from distil.db.sqlalchemy.model_base import DistilBase


class Resource(DistilBase):
    """Database model for storing metadata associated with a resource."""
    __tablename__ = 'resources'
    id = Column(String(100), primary_key=True)
    tenant_id = Column(String(100), ForeignKey("tenants.id"), primary_key=True)
    info = Column(Text)
    created = Column(DateTime, nullable=False)


class UsageEntry(DistilBase):
    """Simplified data store of usage information for a given service

       Similar to ceilometer datastore, but stores local transformed data.
    """

    __tablename__ = 'usage_entry'

    # Service is things like incoming vs. outgoing, as well as instance
    # flavour
    service = Column(String(100), primary_key=True)
    unit = Column(String(100))
    volume = Column(Numeric(precision=20, scale=2), nullable=False)
    resource_id = Column(String(100), primary_key=True)
    tenant_id = Column(String(100), primary_key=True)
    start = Column(DateTime, nullable=False, primary_key=True)
    end = Column(DateTime, nullable=False, primary_key=True)
    created = Column(DateTime, nullable=False)

    resource = relationship(Resource,
                            primaryjoin=(resource_id == Resource.id))
    tenant = relationship(Resource,
                          primaryjoin=(tenant_id == Resource.tenant_id))

    __table_args__ = (ForeignKeyConstraint(
        ["resource_id", "tenant_id"],
        ["resources.id", "resources.tenant_id"],
        name="fk_resource_constraint"
    ),
    )

    @hybrid_property
    def length(self):
        return self.end - self.start

    @hybrid_method
    def intersects(self, other):
        return (self.start <= other.end and other.start <= self.end)

    def __str__(self):
        return ('<UsageEntry {tenant_id=%s resource_id=%s service=%s '
                'start=%s end=%s volume=%s}>' % (self.tenant_id,
                                                 self.resource_id,
                                                 self.service,
                                                 self.start,
                                                 self.end,
                                                 self.volume))


class Tenant(DistilBase):
    """Model for storage of metadata related to a tenant."""
    __tablename__ = 'tenants'
    # ID is a uuid
    id = Column(String(100), primary_key=True, nullable=False)
    name = Column(Text, nullable=False)
    info = Column(Text)
    created = Column(DateTime, nullable=False)
    last_collected = Column(DateTime, nullable=False)

    resources = relationship(Resource, backref="tenant")


class SalesOrder(DistilBase):
    """Historic billing periods."""
    __tablename__ = 'sales_orders'
    id = Column(Integer, primary_key=True)
    tenant_id = Column(
        String(100),
        ForeignKey("tenants.id"),
        primary_key=True)
    start = Column(DateTime, nullable=False, primary_key=True)
    end = Column(DateTime, nullable=False, primary_key=True)

    tenant = relationship("Tenant")

    @hybrid_property
    def length(self):
        return self.end - self.start

    @hybrid_method
    def intersects(self, other):
        return (self.start <= other.end and other.start <= self.end)


class ProjectLock(DistilBase):
    __tablename__ = 'project_locks'

    project_id = Column(String(100), primary_key=True, nullable=False)
    owner = Column(String(100), nullable=False)
    created = Column(DateTime, nullable=False)
