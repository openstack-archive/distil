import requests
import json

# h = httplib2.Http()
from keystoneclient.v2_0 import client
keystone = client.Client(username="admin", password="openstack",
                         tenant_name="demo",
                         auth_url="http://localhost:35357/v2.0")

resources = json.loads(requests.get("http://localhost:8777/v2/resources",
                                    headers={"X-Auth-Token":
                                             keystone.auth_token}).text)
# print json.dumps(resources, indent=True)

r = requests.get(
    "http://localhost:8777/v2/resources",
    headers={"X-Auth-Token": keystone.auth_token,
             "Content-Type": "application/json"},
    data=json.dumps({"q": [
        {"field": "project_id", "op": "eq",
         "value": "8a78fa56de8846cb89c7cf3f37d251d5"}]}))

resources = json.loads(r.text)

fh = open("resources.json", "w")
fh.write(json.dumps(resources, indent=True))
fh.close()


def get(url):
    return json.loads(requests.get(url,
                                   headers={"X-Auth-Token":
                                            keystone.auth_token}).text)

i = 0
for resource in resources:
    
    for link in resource["links"]:
        fh = open("map_fixture_%s.json" % i, "w")
        data_dict = {link["href"]: get(link["href"])}
        fh.write(json.dumps(data_dict, indent=True))
        fh.close()
        i += 1
