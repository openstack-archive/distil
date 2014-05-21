import requests
import json
import urllib
import config

# Provides authentication against Openstack
from keystoneclient.v2_0 import client as KeystoneClient


class NotFound(BaseException):
    pass


class Keystone(KeystoneClient.Client):

    def tenant_by_name(self, name):
        authenticator = self.auth_url
        url = "%(url)s/tenants?%(query)s" % {
            "url": authenticator,
            "query": urllib.urlencode({"name": name})
        }
        r = requests.get(url, headers={
            "X-Auth-Token": self.auth_token,
            "Content-Type": "application/json"
        })
        if r.ok:
            data = json.loads(r.text)
            assert data
            return data
        else:
            if r.status_code == 404:
                # couldn't find it
                raise NotFound

    def get_ceilometer_endpoint(self):
        endpoint = self.service_catalog.url_for(
            service_type="metering",
            endpoint_type="adminURL",
            region_name=config.main['region'])
        return endpoint
