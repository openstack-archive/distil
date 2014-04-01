from novaclient.v1_1 import client
import config


def flavor_name(f_id):
    nova = client.Client(
        config.auth['username'],
        config.auth['password'],
        config.auth['default_tenant'],
        config.auth['end_point'],
        service_type="compute")
    return nova.flavors.get(f_id).name
