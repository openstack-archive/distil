import sys, os

loc = None
try:
    loc, fn = os.path.split(__file__)
except NameError:
    loc = os.getcwd()


sys.path.insert(0, os.path.abspath(os.path.join(loc +"/../artifice")))

from models import usage, resources, tenants, Session, Base
# string = 'postgresql://%(username)s:%(password)s@%(host)s:%(port)s/%(database)s'
# conn_string = string % {'username':'aurynn', 'host':'localhost', 'port':5433, 'password':'aurynn', 'database':'artifice'}

from sqlalchemy import MetaData, create_engine

import os

engine = create_engine( os.environ["DATABASE_URL"] )
Session.configure(bind=engine)

s = Session()

Base.metadata.create_all(engine)