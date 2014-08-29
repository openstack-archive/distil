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

import subprocess
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session,create_session

from sqlalchemy.pool import NullPool
from distil.models import Resource, Tenant, UsageEntry, SalesOrder, Base
from distil import config
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
