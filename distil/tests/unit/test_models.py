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

import datetime
from sqlalchemy.exc import IntegrityError, OperationalError
import unittest
import uuid

from distil.models import Resource, Tenant, UsageEntry, _Last_Run
from distil.tests.unit import test_interface
from distil.tests.unit import utils

TENANT_ID = str(uuid.uuid4())


class TestModels(test_interface.TestInterface):
    def test_create_tenant(self):
        self.session.begin()
        t = Tenant(id=TENANT_ID, name="test",
                   created=datetime.datetime.utcnow(),
                   last_collected=datetime.datetime.utcnow())
        self.session.add(t)
        self.session.commit()
        t2 = self.session.query(Tenant).get(TENANT_ID)
        self.assertEqual(t2.name, "test")
        # self.session.commit()

    def test_create_resource(self):
        self.test_create_tenant()
        self.session.begin()
        t = self.session.query(Tenant).get(TENANT_ID)
        r = Resource(id="1234", info='fake',
                     tenant=t, created=datetime.datetime.utcnow())
        self.session.add(r)
        self.session.commit()
        r2 = self.session.query(Resource).filter(Resource.id == "1234")[0]
        self.assertEqual(r2.tenant.id, t.id)

    def test_insert_usage_entry(self):
        self.test_create_resource()
        self.session.begin()
        r = self.session.query(Resource).filter(Resource.id == "1234")[0]
        u = UsageEntry(service="cheese",
                       volume=1.23,
                       resource=r,
                       tenant=r,
                       start=(datetime.datetime.utcnow() -
                              datetime.timedelta(minutes=5)),
                       end=datetime.datetime.utcnow(),
                       created=datetime.datetime.utcnow())
        self.session.add(u)
        try:
            self.session.commit()
        except Exception as e:
            self.fail("Exception: %s" % e)

    def test_overlapping_usage_entry_fails(self):
        self.test_insert_usage_entry()
        try:
            self.test_insert_usage_entry()
            # we fail here
            #self.fail("Inserted overlapping row; failing")
        except (IntegrityError, OperationalError):
            self.session.rollback()
            self.assertEqual(self.session.query(UsageEntry).count(), 1)

    def test_last_run(self):
        self.session.begin()
        run = _Last_Run(last_run=datetime.datetime.utcnow())
        self.session.add(run)
        self.session.commit()
        result = self.session.query(_Last_Run)
        self.assertEqual(result.count(), 1)
