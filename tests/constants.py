from . import PG_DATABASE_URI

config = {
    "ceilometer": {
        "host": "http://localhost:8777/"
    },
    "main": {
        "export_provider": "tests.mock_exporter:MockExporter",
        "database_uri": PG_DATABASE_URI
    },
    "openstack": {
        "username": "admin",
        "authentication_url": "http://localhost:35357/v2.0",
        "password": "openstack",
        "default_tenant": "demo"
    },
    "export_config": {
        "output_path": "./",
        "delimiter": ",",
        "output_file": "%(tenant)s-%(start)s-%(end)s.csv",
        "rates": {
            "file": "examples/test_rates.csv"
        }
    },
    "artifice": {}
}

TENANTS = [
    {u'enabled': True,
     u'description': None,
     u'name': u'demo',
     u'id': u'3f7b702e4ca14cd99aebf4c4320e00ec'}
]

DATACENTRE = "testcenter"

AUTH_TOKEN = "ASDFTOKEN"
