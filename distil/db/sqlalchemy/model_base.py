# Copyright 2014 Catalyst IT Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo_utils import timeutils
from oslo_db.sqlalchemy import models as oslo_models
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy.ext import declarative
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

from oslo_serialization import jsonutils


class JSONEncodedDict(TypeDecorator):
    """Represents an immutable structure as a json-encoded string."""

    impl = Text

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = jsonutils.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = jsonutils.loads(value)
        return value


class _DistilBase(oslo_models.ModelBase):
    """Base class for all SQLAlchemy DB Models."""
    __table_args__ = {'mysql_engine': 'InnoDB'}

    def keys(self):
        return self.__dict__.keys()

    def values(self):
        return self.__dict__.values()

    def items(self):
        return self.__dict__.items()

    def to_dict(self):
        d = self.__dict__.copy()
        d.pop("_sa_instance_state")
        return d


DistilBase = declarative.declarative_base(cls=_DistilBase)
