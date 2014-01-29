from keystoneclient.v2_0 import client
from flask import request
import flask_restful


def validate_user_in_tenancy(tenant_id):
    headers = request.headers
    if 'user_id' in headers:
        user_id = headers['user_id']
        endpoint = "http://0.0.0.0:35357/v2.0"  # MAJOR TODO
        admin_token = "bob"  # MAJOR TODO
        keystone = client.Client(token=admin_token, endpoint=endpoint)
        tenant = keystone.tenants.get(tenant_id)
        for user in tenant.list_users():
            if user.id == user_id:
                return True
        return False
    else:
        flask_restful.abort(403, message=("'user_id' and 'tenant_id' are" +
                                          "required values."))


def keystone_auth_decorator(func):

    def wrapper(*args, **kwargs):
        if validate_user_in_tenancy(kwargs['id']):
            return func(*args, **kwargs)
        else:
            flask_restful.abort(403, message=("User does not have access" +
                                              "to this tenant."))

    return wrapper
