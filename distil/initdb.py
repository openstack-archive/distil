from models import Base
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool


def provision(engine):

    Base.metadata.create_all(bind=engine)

if __name__ == '__main__':
    import argparse
    a = argparse.ArgumentParser()
    a.add_argument("-uri", "--db_uri", dest="uri", help="Database URI.")

    args = a.parse_args()

    engine = create_engine(args.uri, poolclass=NullPool)
    provision(engine)
