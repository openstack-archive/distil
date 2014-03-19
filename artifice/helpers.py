from novaclient.v1_1 import client


def flavor_name(f_id):
    # Stuff from config:
    print "here?!"
    nova = client.Client("admin", "openstack", "demo",
                         "http://localhost:5000/v2.0",
                         service_type="compute")
    return nova.flavors.get(f_id).name
