import requests
from keystoneclient.v2_0.client import Client as Keystone
from requests.exceptions import ConnectionError
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
                ks.service_catalog.url_for(
                    service_type=kwargs.get('os_service_type'),
                    endpoint_type=kwargs.get('os_endpoint_type')
                )

    def usage(self):
        url = self.endpoint + "collect_usage"

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
        url = self.endpoint + "last_collected"

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

    def sales_order(self, tenants, end, draft):
        if draft:
            url = self.endpoint + "sales_draft"
        else:
            url = self.endpoint + "sales_order"

        headers = {"Content-Type": "application/json",
                   "X-Auth-Token": self.auth_token}

        tenants_resp = {'sales_orders': [], 'errors': {}}
        for tenant in tenants:
            data = {"tenant": tenant, 'end': end}
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

    def sales_historic(self, tenants, date):
        url = self.endpoint + "sales_historic"

        headers = {"Content-Type": "application/json",
                   "X-Auth-Token": self.auth_token}

        tenants_resp = {'sales_orders': [], 'errors': []}
        for tenant in tenants:
            data = {"tenant": tenant, "date": date}
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

    def sales_range(self, tenants, start, end):
        url = self.endpoint + "sales_range"

        tenants_resp = {'sales_orders': [], 'errors': []}

        headers = {"Content-Type": "application/json",
                   "X-Auth-Token": self.auth_token}

        for tenant in tenants:
            data = {"tenant": tenant, "start": start, "end": end}
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
