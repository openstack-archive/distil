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
import sqlalchemy as sa
from sqlalchemy.orm import scoped_session, create_session
from sqlalchemy.pool import NullPool
from distil import models
from sqlalchemy.exc import IntegrityError, OperationalError
from distil.models import Resource, Tenant, UsageEntry, SalesOrder, _Last_Run
import datetime
import uuid

from distil.tests.unit import utils

TENANT_ID = str(uuid.uuid4())

class TestModels(unittest.TestCase):

    def setUp(self):
        engine = sa.create_engine(utils.DATABASE_URI)
        session = scoped_session(lambda: create_session(bind=engine))
        models.Base.metadata.create_all(bind=engine, checkfirst=True)
        self.db = session()

    def tearDown(self):
        try:
            self.db.rollback()
        except:
            pass
        self.db.begin()
        for obj in (SalesOrder, UsageEntry, Resource, Tenant, Resource, _Last_Run):
            self.db.query(obj).delete(synchronize_session="fetch")
        self.db.commit()
        # self.db.close()
        self.db.close()
        # self.session.close_all()
        self.db = None

    def test_create_tenant(self):
        self.db.begin()
        t = Tenant(id=TENANT_ID, name="test",
                   created=datetime.datetime.utcnow(),
                   last_collected=datetime.datetime.utcnow())
        self.db.add(t)
        self.db.commit()
        t2 = self.db.query(Tenant).get(TENANT_ID)
        self.assertEqual(t2.name, "test")
        # self.db.commit()

    def test_create_resource(self):
        self.test_create_tenant()
        self.db.begin()
        t = self.db.query(Tenant).get(TENANT_ID)
        r = Resource(id="1234", info='fake',
                     tenant=t, created=datetime.datetime.utcnow())
        self.db.add(r)
        self.db.commit()
        r2 = self.db.query(Resource).filter(Resource.id == "1234")[0]
        self.assertEqual(r2.tenant.id, t.id)

    def test_insert_usage_entry(self):
        self.test_create_resource()
        self.db.begin()
        r = self.db.query(Resource).filter(Resource.id == "1234")[0]
        u = UsageEntry(service="cheese",
                       volume=1.23,
                       resource=r,
                       tenant=r,
                       start=(datetime.datetime.utcnow() -
                              datetime.timedelta(minutes=5)),
                       end=datetime.datetime.utcnow(),
                       created=datetime.datetime.utcnow())
        self.db.add(u)
        try:
            self.db.commit()
        except Exception as e:
            self.fail("Exception: %s" % e)

    def test_overlapping_usage_entry_fails(self):
        self.test_insert_usage_entry()
        try:
            self.test_insert_usage_entry()
            # we fail here
            #self.fail("Inserted overlapping row; failing")
        except (IntegrityError, OperationalError):
            self.db.rollback()
            self.assertEqual(self.db.query(UsageEntry).count(), 1)

    def test_last_run(self):
        self.db.begin()
        run = _Last_Run(last_run=datetime.datetime.utcnow())
        self.db.add(run)
        self.db.commit()
        result = self.db.query(_Last_Run)
        self.assertEqual(result.count(), 1)
