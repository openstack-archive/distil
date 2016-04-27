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
from sqlalchemy import Numeric
from sqlalchemy import Sequence
from sqlalchemy import String
from sqlalchemy.orm import relationship

from distil.db.sqlalchemy.model_base import JSONEncodedDict
from distil.db.sqlalchemy.model_base import DistilBase


class Resource(DistilBase):
    """Database model for storing metadata associated with a resource.

    """
    __tablename__ = 'resource'
    id = Column(String(64), primary_key=True)
    project_id = Column(String(64), ForeignKey("project.id"),
                        primary_key=True)
    resource_type = Column(String(64), nullable=True)
    meta_data = Column(JSONEncodedDict(), default={})


class Usage(DistilBase):
    """Simplified data store of usage information for a given service,
    in a resource, in a project. Similar to ceilometer datastore,
    but stores local transformed data.
    """
    __tablename__ = 'usage'
    service = Column(String(100), primary_key=True)
    unit = Column(String(255))
    volume = Column(Numeric(precision=20, scale=2), nullable=False)
    resource_id = Column(String(64), ForeignKey('resource.id'),
                         primary_key=True)
    project_id = Column(String(64), ForeignKey('project.id'), primary_key=True)
    start_at = Column(DateTime, nullable=False, primary_key=True)
    end_at = Column(DateTime, nullable=False, primary_key=True)

    @hybrid_property
    def length(self):
        return self.end_at - self.start_at

    @hybrid_method
    def intersects(self, other):
        return (self.start_at <= other.end_at and
                other.start_at <= self.end_at)

    def __str__(self):
        return ('<Usage {project_id=%s resource_id=%s service=%s'
                'start_at=%s end_at =%s volume=%s}>' % (self.project_id,
                                                        self.resource_id,
                                                        self.service,
                                                        self.start_at,
                                                        self.end_at,
                                                        self.volume))


class Project(DistilBase):
    """Model for storage of metadata related to a project.

    """
    __tablename__ = 'project'
    id = Column(String(64), primary_key=True, nullable=False)
    name = Column(String(64), nullable=False)
    meta_data = Column(JSONEncodedDict(), default={})


class LastRun():
    __tablename__ = 'last_run'
    id = Column(Integer, Sequence("last_run_id_seq"), primary_key=True)
    start_at = Column(DateTime, primary_key=True, nullable=False)

# class SalesOrder(DistilBase):
#     """Historic billing periods so that tenants
#        cannot be rebilled accidentally.
#     """
#     __tablename__ = 'sales_orders'
#     id = Column(Integer, primary_key=True)
#     project_id = Column(
#         String(100),
#         ForeignKey("project.id"),
#         primary_key=True)
#     start = Column(DateTime, nullable=False, primary_key=True)
#     end = Column(DateTime, nullable=False, primary_key=True)
# 
#     project = relationship("Project")
# 
#     @hybrid_property
#     def length(self):
#         return self.end - self.start
# 
#     @hybrid_method
#     def intersects(self, other):
#         return (self.start <= other.end and other.start <= self.end)
