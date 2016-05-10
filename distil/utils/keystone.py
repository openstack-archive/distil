# Copyright (C) 2014 Catalyst IT Ltd
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import requests
import json
import urllib
from oslo_config import cfg
from keystoneclient.auth.identity import v2 as v2_auth
from keystoneclient import session
from keystoneclient.v2_0 import client as keystone_client

CONF = cfg.CONF


class KeystoneClient(keystone_client.Client):

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
                raise

    def get_ceilometer_endpoint(self):
        endpoint = self.service_catalog.url_for(service_type="metering",
                                                endpoint_type="adminURL")
        return endpoint


def get_keystone_client():
    auth = v2_auth.Password(
        username=CONF.keystone_authtoken.username,
        password=CONF.keystone_authtoken.password,
        tenant_name=CONF.keystone_authtoken.project_name,
        auth_url=CONF.keystone_authtoken.auth_url)
    valid_session = session.Session(auth=auth)
    return KeystoneClient(session=valid_session)

    