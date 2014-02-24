import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from artifice.models import Resource, Tenant, UsageEntry, SalesOrder

DATABASE_NAME = "test_artifice"

def setUp():
    import subprocess
    subprocess.call(["/usr/bin/createdb","%s" % DATABASE_NAME])

    subprocess.call(["mysql", "-u", "root", "-e", "CREATE DATABASE %s" % DATABASE_NAME])


def tearDown():
    import subprocess
    subprocess.call(["/usr/bin/dropdb","%s" % DATABASE_NAME])

    subprocess.call(["mysql", "-u", "root", "-e", "DROP DATABASE %s" % DATABASE_NAME])

class db(unittest.TestCase):

    __test__ = False
    def setUp(self):
        self.db = sessionmaker(engine=create_engine(self.DATABASE_URI))

    def tearDown(self):
        pass

    def test_create_models(self):
        pass

    def test_create_tenant(self):
        pass

    def test_create_resource(self):
        pass

    def test_insert_usage_entry(self):
        pass
    def test_overwrite_usage_entry_fails(self):
        pass


class TestDatabaseModelsPostgres(db):

    DATABASE_URI = "postgresql://localhost/%s" % DATABASE_NAME
    __test__ = True

class TestDatabaseModelsMysql(db):

    DATABASE_URI = "mysql://localhost/%s" % DATABASE_NAME
    __test__ = True
