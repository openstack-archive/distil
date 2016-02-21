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
from distil.models import UsageEntry, Resource, SalesOrder, _Last_Run
from distil import models
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

import sqlalchemy as sa

from distil.tests.unit import data_samples
from distil.tests.unit import utils

class TestInterface(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super(TestInterface, cls).setUpClass()
        engine = sa.create_engine(getattr(cls, 'db_uri', utils.DATABASE_URI))
        models.Base.metadata.create_all(bind=engine, checkfirst=True)
        Session = sessionmaker(bind=engine)
        cls.session = Session()
        cls.objects = []
        cls.session.rollback()
        cls.called_replacement_resources = False

        cls.resources = (data_samples.RESOURCES["networks"] + 
                          data_samples.RESOURCES["vms"] +
                          data_samples.RESOURCES["objects"] +
                          data_samples.RESOURCES["volumes"] +
                          data_samples.RESOURCES["ips"])

        # TODO: make these constants.
        cls.end = datetime.utcnow()
        cls.start = cls.end - timedelta(days=30)

    @classmethod
    def tearDownClass(cls):
        cls.session.query(UsageEntry).delete()
        cls.session.query(Resource).delete()
        cls.session.query(SalesOrder).delete()
        cls.session.query(tenant_model).delete()
        cls.session.query(_Last_Run).delete()
        cls.session.commit()
        cls.session.close()
        cls.contents = None
        cls.resources = []
        engine = sa.create_engine(getattr(cls, 'db_uri', utils.DATABASE_URI))
