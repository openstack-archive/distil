import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session,create_session
from sqlalchemy.pool import NullPool
from artifice.models import Resource, Tenant, UsageEntry, SalesOrder, Base
import datetime
import subprocess

DATABASE_NAME = "test_artifice"

pg_engine = None
mysql_engine = None

PG_DATABASE_URI = "postgresql://aurynn:postgres@localhost/%s" % DATABASE_NAME
MY_DATABASE_URI = "mysql://root@localhost/%s" % DATABASE_NAME

def setUp():
    subprocess.call(["/usr/bin/createdb","%s" % DATABASE_NAME]) 
    subprocess.call(["mysql", "-u", "root", "-e", "CREATE DATABASE %s" % DATABASE_NAME]) 
    global mysql_engine
    mysql_engine = create_engine(MY_DATABASE_URI, poolclass=NullPool)
    global pg_engine
    pg_engine = create_engine(PG_DATABASE_URI, poolclass=NullPool)

    Base.metadata.create_all(bind=mysql_engine)
    Base.metadata.create_all(bind=pg_engine)


def tearDown():
    pg_engine.dispose()
    mysql_engine.dispose()
    # subprocess.call(["/usr/bin/dropdb","%s" % DATABASE_NAME])  
    # subprocess.call(["mysql", "-u", "root", "-e", "DROP DATABASE %s" % DATABASE_NAME])

class db(unittest.TestCase):
    
    __test__ = False
    def setUp(self):
        # self.maker = sessionmaker(bind=self.engine)
        self.db = self.session()

    def tearDown(self):
        try:
            self.db.rollback()
        except:
            pass
        self.db.begin()
        for obj in (SalesOrder, UsageEntry, Resource, Tenant, Resource):
            self.db.query(obj).delete(synchronize_session="fetch")
        self.db.commit()
        # self.db.close()
        self.db.close()
        # self.session.close_all()
        self.db = None
        # self.maker.close_all()
        # self.maker = None

    def test_create_tenant(self):
        self.db.begin()
        t = Tenant(id="asfd", name="test", created=datetime.datetime.now())
        self.db.add(t)
        self.db.commit()
        t2 = self.db.query(Tenant).get("asfd")
        self.assertTrue(t2.name == "test")
        # self.db.commit()

    def test_create_resource(self):
        self.test_create_tenant()
        self.db.begin()
        t = self.db.query(Tenant).get("asfd")
        r = Resource(id="1234", tenant=t, created=datetime.datetime.now())
        self.db.add(r)
        self.db.commit()
        r2 = self.db.query(Resource).filter(Resource.id == "1234")[0]
        self.assertTrue(r2.tenant.id == t.id)

    def test_insert_usage_entry(self):
        self.test_create_resource()
        self.db.begin()
        t = self.db.query(Tenant).get("asfd")
        r = self.db.query(Resource).filter(Resource.id == "1234")[0]
        u = UsageEntry(service="cheese",
                       volume=1.234,
                       resource=r,
                       tenant=r,
                       start=datetime.datetime.now() - datetime.timedelta(minutes=5),
                       end=datetime.datetime.now(),
                       created=datetime.datetime.now())
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
            self.fail("Inserted overlapping row; failing")
        except Exception as e:
            self.db.rollback()
            self.assertEqual(self.db.query(UsageEntry).count(), 1)

    def test_insert_salesorder(self):
        pass

    def test_overlap_sales_order_fails(self):
        pass


class TestDatabaseModelsPostgres(db):

    __test__ = True
    session = scoped_session(lambda: create_session(bind=pg_engine))

class TestDatabaseModelsMysql(db):

    __test__ = True
    session = scoped_session(lambda: create_session(bind=mysql_engine))
