import requests


class Client(object):

    def __init__(self, endpoint, **kwargs):
        self.endpoint = endpoint
        self.auth_token = kwargs.get('token')

    def usage(self, tenants):
        url = self.endpoint + "usage"
        data = {"tenants": tenants}
        response = requests.post(url,
                                 headers={"Content-Type": "application/json",
                                          "token": self.auth_token},
                                 data=data)
        if response.status_code != 200:
            raise AttributeError("Usage cycle failed: " + response.text +
                                 "  code: " + str(response.status_code))

    def sales_order(self, tenants):
        url = self.endpoint + "sales_order"
        data = {"tenants": tenants}
        response = requests.post(url,
                                 headers={"Content-Type": "application/json",
                                          "token": self.auth_token},
                                 data=data)
        if response.status_code != 200:
            raise AttributeError("Sales order cycle failed: " + response.text +
                                 "  code: " + str(response.status_code))
