from models import Base, __VERSION__
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool


def provision(engine):

    Base.metadata.create_all(bind=engine)

if __name__ == '__main__':
    import argparse
    a = argparse.ArgumentParser()
    a.add_argument("--host", "--host")
    a.add_argument("-p", "--port")
    a.add_argument("-u", "--user")
    a.add_argument("-d", "--database")
    a.add_argument("-P", "--provider")
    a.add_argument("-w", "--password")

    args = a.parse_args()
    conn_string = "{provider}://{user}:{password}@{host}/{database}".format(
        host=args.host,
        port=args.port,
        provider=args.provider,
        user=args.user,
        password=args.password,
        database=args.database)

    engine = create_engine(conn_string, poolclass=NullPool)
    provision(engine)
    
