import requests
from decimal import Decimal


class ClerkNamesMixin(object):

    def pretty_name(self, name):
        url = self.config["clerk"]["url"]
        url = url + "service_types/" + name + "/"
        response = requests.get(url,
                                headers={"Content-Type": "application/json"})
        if response.status_code == 200:
            return str(response.json()['pretty_name'])
        elif response.status_code == 404:
            print "not found"


class ClerkRatesMixin(object):

    def rate(self, name, loc_name):
        url = "http://10.5.36.32/"
        url = (url + "regions/" + loc_name +
               "/services/" + name + "/rates/current/")
        response = requests.get(url,
                                headers={"Content-Type": "application/json"})
        if response.status_code == 200:
            return Decimal(response.json()['rate'])
        elif response.status_code == 404:
            print "not found"
