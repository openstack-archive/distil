import subprocess
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session,create_session

from sqlalchemy.pool import NullPool
from artifice.models import Resource, Tenant, UsageEntry, SalesOrder, Base
from artifice import config
from .constants import DATABASE_NAME, PG_DATABASE_URI, MY_DATABASE_URI
from .constants import config as test_config


def setUp():
    subprocess.call(["/usr/bin/createdb","%s" % DATABASE_NAME]) 
    subprocess.call(["mysql", "-u", "root","--password=password", "-e", "CREATE DATABASE %s" % DATABASE_NAME]) 
    mysql_engine = create_engine(MY_DATABASE_URI, poolclass=NullPool)
    pg_engine = create_engine(PG_DATABASE_URI, poolclass=NullPool)
    Base.metadata.create_all(bind=mysql_engine)
    Base.metadata.create_all(bind=pg_engine)

    mysql_engine.dispose()
    pg_engine.dispose()

    # setup test config:
    config.setup_config(test_config)


def tearDown():

    mysql_engine = create_engine(MY_DATABASE_URI, poolclass=NullPool)
    pg_engine = create_engine(PG_DATABASE_URI, poolclass=NullPool)
    
    Base.metadata.drop_all(bind=mysql_engine)
    Base.metadata.drop_all(bind=pg_engine)

    mysql_engine.dispose()
    pg_engine.dispose()


    subprocess.call(["/usr/bin/dropdb","%s" % DATABASE_NAME])  
    subprocess.call(["mysql", "-u", "root", "--password=password", "-e", "DROP DATABASE %s" % DATABASE_NAME])
