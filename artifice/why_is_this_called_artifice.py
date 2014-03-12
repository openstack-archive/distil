import yaml
from artifice.models import Session
from interface import Artifice
default_config = "/etc/artifice/config.yaml"

def connect(config=None):

    if config is None:
        try:
            fh = open(default_config)
        except IOError:
            print "Can't open default config!"
            raise
        config = yaml.load( fh.read() )
    # conn_string = 'postgresql://%(username)s:%(password)s@%(host)s:%(port)s/%(database)s' % {
    #     "username": config["database"]["username"],
    #     "password": config["database"]["password"],
    #     "host":     config["database"]["host"],
    #     "port":     config["database"]["port"],
    #     "database": config["database"]["database"]
    # }
    # engine = create_engine(conn_string)
    # session.configure(bind=engine)
    artifice = Artifice(config)
    # artifice.artifice = session
    return artifice
