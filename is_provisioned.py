from artifice.models import Base, __VERSION__, _Version
from sqlalchemy.orm import scoped_session, create_session
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool
import sys, os

uri = os.environ["DATABASE_URI"]
engine = create_engine(uri, poolclass=NullPool)
session = create_session(bind=engine)

v = session.query(_Version).first()
if v is None:
    sys.exit(0)

sys.exit(1)
