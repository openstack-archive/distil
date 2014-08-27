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
from requests.exceptions import ConnectionError
import json


class Client(object):

    def __init__(self, endpoint, **kwargs):
        self.endpoint = endpoint
        self.auth_token = kwargs.get('token')

    def usage(self):
        url = self.endpoint + "collect_usage"
        try:
            response = requests.post(url,
                                     headers={"Content-Type":
                                              "application/json",
                                              "token": self.auth_token})
            if response.status_code != 200:
                raise AttributeError("Usage cycle failed: " + response.text +
                                     "  code: " + str(response.status_code))
            else:
                return response.json()
        except ConnectionError as e:
            print e

    def sales_order(self, tenants, end, draft):
        if draft:
            url = self.endpoint + "sales_draft"
        else:
            url = self.endpoint + "sales_order"

        tenants_resp = {'sales_orders': [], 'errors': {}}
        for tenant in tenants:
            data = {"tenant": tenant, 'end': end}
            try:
                response = requests.post(url,
                                         headers={"Content-Type":
                                                  "application/json",
                                                  "token": self.auth_token},
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

    def sales_historic(self, tenants, date):
        url = self.endpoint + "sales_historic"

        tenants_resp = {'sales_orders': [], 'errors': []}
        for tenant in tenants:
            data = {"tenant": tenant, "date": date}
            try:
                response = requests.post(url,
                                         headers={"Content-Type":
                                                  "application/json",
                                                  "token": self.auth_token},
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

    def sales_range(self, tenants, start, end):
        url = self.endpoint + "sales_range"

        tenants_resp = {'sales_orders': [], 'errors': []}
        for tenant in tenants:
            data = {"tenant": tenant, "start": start, "end": end}
            try:
                response = requests.post(url,
                                         headers={"Content-Type":
                                                  "application/json",
                                                  "token": self.auth_token},
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
