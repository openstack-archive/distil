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

from datetime import datetime, timedelta
import unittest
import sqlalchemy as sa
from sqlalchemy.orm import scoped_session, create_session
from sqlalchemy.orm import sessionmaker

from distil.models import UsageEntry, Resource, SalesOrder, Tenant, _Last_Run
from distil import models
from distil.tests.unit import data_samples


class TestInterface(unittest.TestCase):
    def setUp(self):
        super(TestInterface, self).setUp()

        # self.engine = sa.create_engine('sqlite:////tmp/distil.db')
        # Session = sessionmaker(bind=self.engine)
        # self.session = Session()
        #
        # models.Base.metadata.create_all(bind=self.engine, checkfirst=True)

        self.engine = sa.create_engine('sqlite:////tmp/distil.db')
        session = scoped_session(lambda: create_session(bind=self.engine))
        models.Base.metadata.create_all(bind=self.engine, checkfirst=True)
        self.session = session()

        self.objects = []
        self.called_replacement_resources = False

        self.resources = (data_samples.RESOURCES["networks"] +
                          data_samples.RESOURCES["vms"] +
                          data_samples.RESOURCES["objects"] +
                          data_samples.RESOURCES["volumes"] +
                          data_samples.RESOURCES["ips"])

        # TODO: make these constants.
        self.end = datetime.utcnow()
        self.start = self.end - timedelta(days=30)

    def tearDown(self):
        try:
            self.session.rollback()
        except:
            pass
        self.session.begin()
        for obj in (SalesOrder, UsageEntry, Resource, Tenant, Resource,
                    _Last_Run):
            self.session.query(obj).delete(synchronize_session="fetch")
        self.session.commit()
        self.session.close()
        self.session = None

        # for obj in (SalesOrder, UsageEntry, Resource, Tenant, _Last_Run):
        #     self.session.query(obj).delete()
        # self.session.commit()
        # self.session.close()
        # self.session = None

        self.contents = None
        self.resources = []
