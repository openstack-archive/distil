import unittest
from artifice.models import usage, tenants, resources, Session
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy.orm.exc import FlushError
import os

from artifice.models.usage import Usage
from artifice.models.tenants import Tenant
from artifice.models.resources import Resource

from datetime import datetime, timedelta

TENANT_ID = "test tenant"
RESOURCE_ID = "test resource"
RESOURCE_ID_TWO = "A DIFFERENT RESOURCE"

USAGE_ID = 12345


class SessionBase(unittest.TestCase):

    def setUp(self):

        engine = create_engine(os.environ["DATABASE_URL"])
        Session.configure(bind=engine)
        self.session = Session()

        self.objects = []

        self.session.rollback()

    def tearDown(self):

        self.session.rollback()

        for t in self.objects:
            try:
                self.session.delete(t)
            except InvalidRequestError:
                # This is fine
                pass

        self.session.commit()
        self.session = None


class TestTenant(SessionBase):

    def test_create_tenant(self):

        t = tenants.Tenant()
        self.objects.append(t)
        t.id = TENANT_ID
        self.session.add(t)
        self.session.flush()
        self.session.commit()


        t2 = self.session.query(tenants.Tenant)\
            .filter(tenants.Tenant.id == TENANT_ID)[0]

        self.assertTrue( t2 is not None )
        self.assertEqual( t2.id, TENANT_ID )


    def test_create_identical_tenant_fails(self):

        # First pass
        self.test_create_tenant()
        try:
            self.test_create_tenant()
        except (IntegrityError, FlushError) as e:
            self.assertTrue ( True )
        except Exception as e:
            # self.fail ( e.__class__ )
            self.fail ( e )


class TestResource(SessionBase):

    def test_create_resource(self):
        r = resources.Resource()
        t = tenants.Tenant()
        t.id = TENANT_ID

        r.tenant = t
        r.id = RESOURCE_ID
        self.session.add(r)
        self.session.add(t)
        self.objects.extend((r,t))
        self.session.flush()
        self.session.commit()

        r2 = self.session.query(resources.Resource)\
            .filter(resources.Resource.id == RESOURCE_ID)[0]

        self.assertEqual(r2.id, r.id)
        self.assertEqual( r2.tenant.id, t.id )


    def test_create_resource_with_bad_tenant_fails(self):

        r = resources.Resource()

        t = tenants.Tenant()
        r.tenant = t

        self.objects.extend((r,t))

        self.session.add(r)
        self.session.add(t)
        try:
            self.session.commit()
        except IntegrityError:
            self.assertTrue(True)
        except Exception as e:
            self.fail(e)

    def test_create_resource_without_tenant_fails(self):

        r = resources.Resource()
        r.id = RESOURCE_ID
        self.session.add(r)

        self.objects.append(r)

        try:
            self.session.commit()
        except IntegrityError:
            self.assertTrue(True)
        except Exception as e:
            self.fail(e)


class TestUsage(SessionBase):

    """Tests various states of the Usage objects."""

    # def setUp(self):
    #     super(TestUsage, self).setUp()

    #     self.resource

    # def tearDown(self):
    #     pass

    def test_save_usage_to_database(self):
        r = Resource()
        r.id = RESOURCE_ID

        t = Tenant()

        t.id = TENANT_ID

        r.tenant = t

        self.objects.extend((r, t))

        start = datetime.now() - timedelta(days=30)
        end = datetime.now()

        u = Usage(r, t, 1, start, end )
        u.id = USAGE_ID

        self.objects.append(u)

        self.session.add(u)
        self.session.add(r)
        self.session.add(t)

        self.session.commit()

        u2 = self.session.query(Usage)[0]

        self.assertTrue( u2.resource.id == r.id )
        self.assertTrue( u2.tenant.tenant.id == t.id )
        self.assertTrue( u2.created == u.created )
        print u2.time

    def test_overlap_throws_exception(self):

        self.test_save_usage_to_database()

        r = self.session.query(Resource).filter(Resource.id == RESOURCE_ID)[0]
        t = self.session.query(Tenant).filter(Tenant.id == TENANT_ID)[0]

        start = datetime.now() - timedelta(days=15)
        end = datetime.now()

        u2 = Usage(r, t, 2, start, end)

        self.session.add(u2)
        try:
            self.session.commit()
        except IntegrityError:
            self.assertTrue(True)
        except Exception as e:
            self.fail(e)

    def test_overlap_with_different_resource_succeeds(self):

        self.test_save_usage_to_database()

        t = self.session.query(Tenant).filter(Tenant.id == TENANT_ID)[0]
        r = Resource()
        r.id = RESOURCE_ID_TWO
        r.tenant = t

        start = datetime.now() - timedelta(days=30)
        end = datetime.now()

        u = Usage(r, t, 2, start, end)

        self.objects.extend((r, u))
        self.session.add(u)
        self.session.add(r)

        try:
            self.session.commit()
        except IntegrityError as e:
            self.fail("Integrity violation: %s" % e)
        except Exception as e:
            self.fail("Major exception: %s" % e)

    def test_non_overlap_succeeds(self):
        self.test_save_usage_to_database()

        r = self.session.query(Resource).filter(Resource.id == RESOURCE_ID)[0]
        t = self.session.query(Tenant).filter(Tenant.id == TENANT_ID)[0]

        start = datetime.now()
        end = datetime.now() + timedelta(days=30)

        u = Usage(r, t, 1, start, end)

        self.session.add(u)

        try:
            self.session.commit()
            self.objects.append(u)
        except IntegrityError as e:
            self.fail("Integrity violation: %s" % e)
        except Exception as e:
            self.fail("Fail: %s" % e)

    def test_tenant_does_not_exist_fails(self):

        pass

    def test_resource_does_not_exist_fails(self):
        pass

    def test_resource_belongs_to_different_tenant_fails(self):
        self.test_save_usage_to_database()
        t = Tenant()
        t.id = "TENANT TWO"

        r = self.session.query(Resource).filter(Resource.id == RESOURCE_ID)[0]
        start = datetime.now()
        end = datetime.now() + timedelta(days=30)
        self.session.add(t)

        self.objects.append(t)

        try:
            u = Usage(r, t, 1, start, end)
            self.session.commit()
            self.objects.append(u)
            self.fail("Should not have saved!")
        except (IntegrityError, AssertionError) as e :
            self.assertTrue(True) # Pass
        except Exception as e:

            self.fail(e.__class__)

