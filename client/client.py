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
from keystoneclient.v2_0.client import Client as Keystone
from requests.exceptions import ConnectionError
from urlparse import urljoin


class Client(object):

    def __init__(self, distil_url=None, os_auth_token=None,
                 os_username=None, os_password=None,
                 os_tenant_id=None, os_tenant_name=None,
                 os_auth_url=None, os_region_name=None,
                 os_cacert=None, insecure=False,
                 os_service_type='rating', os_endpoint_type='publicURL'):

        self.insecure = insecure

        if os_auth_token and distil_url:
            self.auth_token = os_auth_token
            self.endpoint = distil_url
        else:
            ks = Keystone(username=os_username,
                          password=os_password,
                          tenant_id=os_tenant_id,
                          tenant_name=os_tenant_name,
                          auth_url=os_auth_url,
                          region_name=os_region_name,
                          cacert=os_cacert,
                          insecure=insecure)
            if os_auth_token:
                self.auth_token = os_auth_token
            else:
                self.auth_token = ks.auth_token

            if distil_url:
                self.endpoint = distil_url
            else:
                self.endpoint = ks.service_catalog.url_for(
                    service_type=os_service_type,
                    endpoint_type=os_endpoint_type
                )

    def collect_usage(self):
        url = urljoin(self.endpoint, "collect_usage")

        headers = {"Content-Type": "application/json",
                   "X-Auth-Token": self.auth_token}

        try:
            response = requests.post(url, headers=headers,
                                     verify=not self.insecure)
            if response.status_code != 200:
                raise AttributeError("Usage cycle failed: %s  code: %s" %
                                     (response.text, response.status_code))
            else:
                return response.json()
        except ConnectionError as e:
            print e

    def last_collected(self):
        url = urljoin(self.endpoint, "last_collected")

        headers = {"Content-Type": "application/json",
                   "X-Auth-Token": self.auth_token}

        try:
            response = requests.get(url, headers=headers,
                                    verify=not self.insecure)
            if response.status_code != 200:
                raise AttributeError("Get last collected failed: %s code: %s" %
                                     (response.text, response.status_code))
            else:
                return response.json()
        except ConnectionError as e:
            print e

    def get_usage(self, tenant, start, end):
        return self._query_usage(tenant, start, end, "get_usage")

    def get_rated(self, tenant, start, end):
        return self._query_usage(tenant, start, end, "get_rated")

    def _query_usage(self, tenant, start, end, endpoint):
        url = urljoin(self.endpoint, endpoint)

        headers = {"X-Auth-Token": self.auth_token}

        params = {"tenant": tenant,
                  "start": start,
                  "end": end
                  }

        try:
            response = requests.get(url, headers=headers,
                                    params=params,
                                    verify=not self.insecure)
            if response.status_code != 200:
                raise AttributeError("Get usage failed: %s code: %s" %
                                     (response.text, response.status_code))
            else:
                return response.json()
        except ConnectionError as e:
            print e
