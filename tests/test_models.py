import unittest
from artifice.models import usage, tenants, resources, Session
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy.orm.exc import FlushError
import os


class TestTenant(unittest.TestCase):

    ID = "test tenant"

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


    def test_create_tenant(self):

        t = tenants.Tenant()
        self.objects.append(t)
        t.id = self.ID
        self.session.add(t)
        self.session.flush()
        self.session.commit()


        t2 = self.session.query(tenants.Tenant)\
            .filter(tenants.Tenant.id == self.ID)[0]

        self.assertTrue( t2 is not None )
        self.assertEqual( t2.id, self.ID )


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


class TestResource(unittest.TestCase):

    def test_create_resource(self):
        pass

    def test_create_resource_with_bad_tenant(self):
        pass

    def test_create_resource_without_tenant(self):
        pass



class TestUsage(unittest.TestCase):

    """Tests various states of the Usage objects."""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_save_to_database(self):
        pass

    def test_overlap_throws_exception(self):
        pass

    def test_non_overlap_does_not_throw_exception(self):
        pass

    def test_tenant_does_not_exist(self):
        pass

    def test_resource_does_not_exist(self):
        pass