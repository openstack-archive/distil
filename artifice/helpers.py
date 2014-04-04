from novaclient.v1_1 import client
import config

cache = {}

def flavor_name(f_id):
    f_id = int(f_id)

    if f_id not in cache:
        nova = client.Client(
            config.auth['username'],
            config.auth['password'],
            config.auth['default_tenant'],
            config.auth['end_point'],
            service_type="compute",
            insecure=config.auth['insecure'])

        cache[f_id] = nova.flavors.get(f_id).name
    return cache[f_id]
