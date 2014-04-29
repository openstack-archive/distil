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

        except ConnectionError as e:
            print e

    def sales_order(self, tenants, draft):
        if draft:
            url = self.endpoint + "sales_draft"
        else:
            url = self.endpoint + "sales_order"

        for tenant in tenants:
            data = {"tenant": tenant}
            try:
                response = requests.post(url,
                                         headers={"Content-Type":
                                                  "application/json",
                                                  "token": self.auth_token},
                                         data=json.dumps(data))
                if response.status_code != 200:
                    raise AttributeError("Sales order cycle failed: " +
                                         response.text + "  code: " +
                                         str(response.status_code))
                else:
                    print json.dumps(response.json(), indent=2, sort_keys=True)
            except ConnectionError as e:
                print e
