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

# from test data:
TENANT_ID = "cd3deadd3d5a4f11802d03928195f4ef"

TENANTS = [
    {u'enabled': True,
     u'description': None,
     u'name': u'demo',
     u'id': u'cd3deadd3d5a4f11802d03928195f4ef'}
]

AUTH_TOKEN = "ASDFTOKEN"
