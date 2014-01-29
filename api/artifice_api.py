from flask import Flask, jsonify, abort, make_response
from flask.ext.restful import Api, Resource, reqparse, fields, marshal
from keystone_api import keystone_auth_decorator


app = Flask(__name__, static_url_path="")
api = Api(app)


service_list = {"serv1": "Service 1", "serv2": "Service 2",
                "serv3": "Service 3", "serv4": "Service 4",
                "serv5": "Service 5", "serv6": "Service 6"}


billed_months = {"bills": [{"date": "Oct, 2013",
                  "charges":
                  {"Service 1": "56", "Service 2": "32",
                   "Service 3": "45", "Service 4": "28",
                   "Service 5": "42"}
                  },
                 {"date": "Nov, 2013",
                  "charges":
                  {"Service 2": "16",
                   "Service 3": "45.4", "Service 4": "28",
                   "Service 5": "42.25"}
                  },
                 {"date": "Dec, 2013",
                  "charges":
                  {"Service 1": "23", "Service 2": "89",
                   "Service 3": "62", "Service 4": "89",
                   "Service 5": "99", "Service 6": "66"}
                  },
                 {"date": "Jan, 2014",
                  "charges":
                  {"Service 1": "25", "Service 2": "12",
                   "Service 3": "43.2", "Service 4": "60",
                   "Service 5": "86", "Service 6": "32"}
                  }]
		}

unbilled_month = {"date": "Feb, 2014",
                  "charges":
                  {"Service 1": "12", "Service 2": "11.2",
                   "Service 3": "12", "Service 4": "35",
                   "Service 5": "55.7", "Service 6": "23"}
                  }



class BillAPI(Resource):
    decorators = [keystone_auth_decorator]

    def get(self, id):
        return billed_months


class UnbilledAPI(Resource):
    decorators = [keystone_auth_decorator]

    def get(self, id):
        return unbilled_month


class ServiceList(Resource):

    def get(self):
        return service_list


api.add_resource(BillAPI, '/artifice/bills/<string:id>', endpoint='bills')
api.add_resource(UnbilledAPI, '/artifice/bills/<string:id>/unbilled',
                 endpoint='unbilled')
api.add_resource(ServiceList, '/artifice/service_list', endpoint='services')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=2000)
