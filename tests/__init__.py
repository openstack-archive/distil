import subprocess
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session,create_session

from sqlalchemy.pool import NullPool
from artifice.models import Resource, Tenant, UsageEntry, SalesOrder, Base

DATABASE_NAME = "test_artifice"

PG_DATABASE_URI = "postgresql://aurynn:postgres@localhost/%s" % DATABASE_NAME
MY_DATABASE_URI = "mysql://root:password@localhost/%s" % DATABASE_NAME

def setUp():
    subprocess.call(["/usr/bin/createdb","%s" % DATABASE_NAME]) 
    subprocess.call(["mysql", "-u", "root","--password=password", "-e", "CREATE DATABASE %s" % DATABASE_NAME]) 
    mysql_engine = create_engine(MY_DATABASE_URI, poolclass=NullPool)
    pg_engine = create_engine(PG_DATABASE_URI, poolclass=NullPool)
    Base.metadata.create_all(bind=mysql_engine)
    Base.metadata.create_all(bind=pg_engine)

    mysql_engine.dispose()
    pg_engine.dispose()

def tearDown():

    mysql_engine = create_engine(MY_DATABASE_URI, poolclass=NullPool)
    pg_engine = create_engine(PG_DATABASE_URI, poolclass=NullPool)
    
    Base.metadata.drop_all(bind=mysql_engine)
    Base.metadata.drop_all(bind=pg_engine)

    mysql_engine.dispose()
    pg_engine.dispose()


    subprocess.call(["/usr/bin/dropdb","%s" % DATABASE_NAME])  
    subprocess.call(["mysql", "-u", "root", "--password=password", "-e", "DROP DATABASE %s" % DATABASE_NAME])
