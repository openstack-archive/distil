import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session,create_session
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
    mysql_engine = create_engine(MY_DATABASE_URI)
    global pg_engine
    pg_engine = create_engine(PG_DATABASE_URI)

    Base.metadata.create_all(bind=mysql_engine)
    Base.metadata.create_all(bind=pg_engine)


def tearDown():
    pg_engine.dispose()
    mysql_engine.dispose()
    subprocess.call(["/usr/bin/dropdb","%s" % DATABASE_NAME])  
    subprocess.call(["mysql", "-u", "root", "-e", "DROP DATABASE %s" % DATABASE_NAME])

class db(unittest.TestCase):
    
    __test__ = False
    def setUp(self):
        # self.maker = sessionmaker(bind=self.engine)
        self.db = self.session()

    def tearDown(self):
        for obj in (Tenant, Resource, UsageEntry, SalesOrder):
            self.db.query(obj).delete()
        self.db.close()
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

    def test_create_resource(self):
        pass

    def test_insert_usage_entry(self):
        pass
    def test_overwrite_usage_entry_fails(self):
        pass


class TestDatabaseModelsPostgres(db):

    __test__ = True
    session = scoped_session(lambda: create_session(bind=pg_engine))

class TestDatabaseModelsMysql(db):

    __test__ = True
    session = scoped_session(lambda: create_session(bind=mysql_engine))
