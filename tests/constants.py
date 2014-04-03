
DATABASE_NAME = "test_artifice"

PG_DATABASE_URI = "postgresql://aurynn:postgres@localhost/%s" % DATABASE_NAME
MY_DATABASE_URI = "mysql://root:password@localhost/%s" % DATABASE_NAME


config = {
    "main": {
        "region": "Wellington",
        "timezone": "Pacific/Auckland",
        "export_provider": "tests.mock_exporter:MockExporter",
        "database_uri": PG_DATABASE_URI
    },
    "export_config": {
        "output_path": "./",
        "delimiter": ",",
        "output_file": "%(tenant)s-%(start)s-%(end)s.csv",
        "rates": {
            "file": "examples/test_rates.csv"
        }
    },
    "auth": {
        "end_point": "http://localhost:35357/v2.0",
        "username": "admin",
        "password": "openstack",
        "default_tenant": "demo",
        "insecure": False,
    },
    "ceilometer": {
        "host": "http://localhost:8777/"
    },
    "transformers": {
        "uptime": {
            "tracked_states": ["active", "building",
                               "paused", "rescued", "resized"]
        }
    }
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
