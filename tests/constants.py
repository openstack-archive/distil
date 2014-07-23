
DATABASE_NAME = "test_distil"

PG_DATABASE_URI = "postgresql://aurynn:postgres@localhost/%s" % DATABASE_NAME
MY_DATABASE_URI = "mysql://root:password@localhost/%s" % DATABASE_NAME


config = {
    "main": {
        "region": "Wellington",
        "timezone": "Pacific/Auckland",
        "database_uri": PG_DATABASE_URI,
        "log_file": "logs/tests.log"
    },
    "rates_config": {
        "file": "examples/test_rates.csv"
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
        },
        "from_image": {
            "service": "volume.size",
            "md_keys": ["image_ref", "image_meta.base_image_ref"],
            "none_values": ["None", ""],
            "size_keys": ["root_gb"]
        }
    },
    "collection": {}
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
