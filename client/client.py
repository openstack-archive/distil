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
import json


class Client(object):

    def __init__(self, distil_url=None, os_auth_token=None, **kwargs):
        if os_auth_token and distil_url:
            self.auth_token = os_auth_token
            self.endpoint = distil_url
        else:
            ks = Keystone(username=kwargs.get('os_username'),
                          password=kwargs.get('os_password'),
                          tenant_id=kwargs.get('os_tenant_id'),
                          tenant_name=kwargs.get('os_tenant_name'),
                          auth_url=kwargs.get('os_auth_url'),
                          region_name=kwargs.get('os_region_name'),
                          cacert=kwargs.get('os_cacert'),
                          insecure=kwargs.get('insecure'))
            if os_auth_token:
                self.auth_token = os_auth_token
            else:
                self.auth_token = ks.auth_token

            if distil_url:
                self.endpoint = distil_url
            else:
                self.endpoint = ks.service_catalog.url_for(
                    service_type=kwargs.get('os_service_type', 'rating'),
                    endpoint_type=kwargs.get('os_endpoint_type', 'publicURL')
                )

    def usage(self):
        url = urljoin(self.endpoint, "collect_usage")

        headers = {"Content-Type": "application/json",
                   "X-Auth-Token": self.auth_token}

        try:
            response = requests.post(url, headers=headers)
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
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                raise AttributeError("Get last collected failed: %s code: %s" %
                                     (response.text, response.status_code))
            else:
                return response.json()
        except ConnectionError as e:
            print e

    def get_usage(self, tenant, start, end):
        url = urljoin(self.endpoint, "get_usage")

        headers = {
                "X-Auth-Token": self.auth_token
                }

        params = {
                "tenant": tenant,
                "start": start,
                "end": end
                }

        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code != 200:
                raise AttributeError("Get usage failed: %s code: %s" %
                        (response.text, response.status_code))
            else:
                return response.json()
        except ConnectionError as e:
            print e

    def _sales_order_query(self, tenants, relative_url, make_data):
        url = urljoin(self.endpoint, relative_url)

        headers = {"Content-Type": "application/json",
                   "X-Auth-Token": self.auth_token}

        tenants_resp = {'sales_orders': [], 'errors': {}}
        for tenant in tenants:
            data = make_data(tenant)
            try:
                response = requests.post(url, headers=headers,
                                         data=json.dumps(data))
                if response.status_code != 200:
                    error = ("Sales order cycle failed: %s Code: %s" %
                            (response.text, response.status_code))
                    tenants_resp['errors'][tenant] = error
                else:
                    tenants_resp['sales_orders'].append(response.json())
            except ConnectionError as e:
                print e
        return tenants_resp

    def sales_order(self, tenants, end, draft):
        return self._sales_order_query(
            tenants,
            'sales_draft' if draft else 'sales_order',
            lambda tenant: {'tenant': tenant, 'end': end}
            )

    def sales_historic(self, tenants, date):
        return self._sales_order_query(
            tenants,
            'sales_historic',
            lambda tenant: {'tenant': tenant, 'date': date}
            )

    def sales_range(self, tenants, start, end):
        return self._sales_order_query(
            tenants,
            'sales_range',
            lambda tenant: {'tenant': tenant, 'start': start, 'end': end}
            )
