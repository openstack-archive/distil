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

import unittest
from distil.models import Tenant as tenant_model
from distil.models import UsageEntry, Resource, SalesOrder
from sqlalchemy.pool import NullPool

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from datetime import datetime, timedelta

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

from . import PG_DATABASE_URI
from .data_samples import RESOURCES


class TestInterface(unittest.TestCase):

    def setUp(self):

        engine = create_engine(PG_DATABASE_URI, poolclass=NullPool)
        Session = sessionmaker(bind=engine)
        self.session = Session()
        self.objects = []
        self.session.rollback()
        self.called_replacement_resources = False

        self.resources = (RESOURCES["networks"] + RESOURCES["vms"] +
                          RESOURCES["objects"] + RESOURCES["volumes"] +
                          RESOURCES["ips"])

        # TODO: make these constants.
        self.end = datetime.utcnow()
        self.start = self.end - timedelta(days=30)

    def tearDown(self):

        self.session.query(UsageEntry).delete()
        self.session.query(Resource).delete()
        self.session.query(SalesOrder).delete()
        self.session.query(tenant_model).delete()
        self.session.commit()
        self.session.close()
        self.contents = None
        self.resources = []
