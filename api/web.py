import flask
from flask import Flask, abort, Blueprint
from artifice import interface, database
from artifice.models import UsageEntry, SalesOrder, Tenant, billing
import sqlalchemy
from sqlalchemy import create_engine, func
from sqlalchemy.orm import scoped_session, create_session
from sqlalchemy.pool import NullPool
from decimal import Decimal
from datetime import datetime
from decorator import decorator
import collections
import itertools
import pytz
import json


engine = None
# Session.configure(bind=create_engine(conn_string))

Session = None
# db = Session()

app = Blueprint("main", __name__)

config = None

invoicer = None

DEFAULT_TIMEZONE = "Pacific/Auckland"

current_region = "Wellington"  # FIXME


def get_app(conf):
    actual_app = Flask(__name__)
    actual_app.register_blueprint(app, url_prefix="/")

    global engine
    engine = create_engine(conf["main"]["database_uri"], poolclass=NullPool)

    global config
    config = conf

    global Session
    Session = scoped_session(lambda: create_session(bind=engine))

    global invoicer
    module, kls = config["main"]["export_provider"].split(":")
    invoicer = __import__(module, globals(), locals(), [kls])

    if config["main"].get("timezone"):
        global DEFAULT_TIMEZONE
        DEFAULT_TIMEZONE = config["main"]["timezone"]

    return actual_app


# Some useful constants
iso_time = "%Y-%m-%dT%H:%M:%S"
iso_date = "%Y-%m-%d"
dawn_of_time = "2012-01-01"


class validators(object):

    @classmethod
    def iterable(cls, val):
        return isinstance(val, collections.Iterable)


class DecimalEncoder(json.JSONEncoder):
    """Simple encoder which handles Decimal objects, rendering them to strings.
    *REQUIRES* use of a decimal-aware decoder.
    """
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return json.JSONEncoder.default(self, obj)


def fetch_endpoint(region):
    return config.get("keystone_endpoint")
    # return "http://0.0.0.0:35357/v2.0" # t\/his ought to be in config. #FIXME


def keystone(func):
    """Will eventually provide a keystone wrapper for validating a query.
    Currently does not.
    """
    return func  # disabled for now
    # admin_token = config.get("admin_token")
    # def _perform_keystone(*args, **kwargs):
    #     headers = flask.request.headers
    #     if not 'user_id' in headers:
    #         flask.abort(401) # authentication required
    #
    #     endpoint = fetch_endpoint( current_region )
    #     keystone = keystoneclient.v2_0.client.Client(token=admin_token,
    #             endpoint=endpoint)

    # return _perform_keystone


def must(*args, **kwargs):
    """
    Asserts that a given set of keys are present in the request parameters.
    Also allows for keyword args to handle validation.
    """
    def tester(func):
        def funky(*iargs, **ikwargs):
            body = flask.request.params
            for key in itertools.chain(args, kwargs.keys()):
                if not key in body:
                    abort(403)
                    return json.dumps({"error": "missing parameter",
                                       "param": key})
            for key, val in kwargs.iteritems():
                input_ = body[key]
                if not val(input_):
                    abort(403)
                    return json.dumps({"error": "validation failed",
                                       "param": key})
            return func(*iargs, **ikwargs)
        return decorator(funky, func)
    return tester


@decorator
def returns_json(func, *args, **kwargs):
    status, content = func(*args, **kwargs)
    response = flask.make_response(
        json.dumps(content), status)
    response.headers['Content-type'] = 'application/json'
    return response


def json_must(*args, **kwargs):
    """Implements a simple validation system to allow for the required
       keys to be detected on a given callable."""
    def unpack(func):
        def dejson(f, *iargs):
            if flask.request.headers["content-type"] != "application/json":
                abort(403, json.dumps({"error": "must be in JSON format"}))
            # todo -- parse_float was handled specially
            body = flask.request.json
            for key in itertools.chain(args, kwargs.keys()):
                if not key in body:
                    abort(403, json.dumps({"error": "missing key",
                                           "key": key}))
            for key, val in kwargs.iteritems():
                input_ = body[key]
                if not val(input_):
                    abort(403, json.dumps({"error": "validation failed",
                                           "key": key}))

            return func(*iargs)
        return decorator(dejson, func)
    return unpack


@app.route("collect_usage", methods=["POST"])
@keystone
def run_usage_collection():
    """
    Adds usage for a given tenant T and resource R.
    Expects to receive a Resource ID, a time range, and a volume.

    The volume will be parsed from JSON as a Decimal object.
    """

    session = Session()

    artifice = interface.Artifice(config)
    d = database.Database(session)

    tenants = artifice.tenants

    resp = {"tenants": [],
            "errors": 0}

    for tenant in tenants:
        d.insert_tenant(tenant.conn['id'], tenant.conn['name'],
                        tenant.conn['description'])
        session.begin(subtransactions=True)
        start = session.query(func.max(UsageEntry.end).label('end')).\
            filter(UsageEntry.tenant_id == tenant.conn['id']).first().end
        if not start:
            start = datetime.strptime(dawn_of_time, iso_date)

        end = datetime.now(pytz.timezone(DEFAULT_TIMEZONE)).\
            replace(minute=0, second=0, microsecond=0)

        usage = tenant.usage(start, end)
        # .values() returns a tuple of lists of artifice Resource models
        # enter expects a list of direct resource models.
        # So, unwind the list.
        for resource in usage.values():
            d.enter(resource, start, end)
        try:
            session.commit()
            resp["tenants"].append(
                {"id": tenant.conn['id'],
                 "updated": True,
                 "start": start.strftime(iso_time),
                 "end": end.strftime(iso_time)
                 }
            )
        except sqlalchemy.exc.IntegrityError:
            # this is fine.
            resp["tenants"].append(
                {"id": tenant.conn['id'],
                 "updated": False,
                 "error": "Integrity error",
                 "start": start.strftime(iso_time),
                 "end": end.strftime(iso_time)
                 }
            )
            resp["errors"] += 1
    session.close()
    return json.dumps(resp)


@app.route("sales_order", methods=["POST"])
@keystone
@json_must("tenants")
@returns_json
def run_sales_order_generation():

    session = Session()
    d = database.Database(session)

    t = flask.request.json.get("tenants", None)
    tenants = session.query(Tenant)
    if t:
        tenants = tenants.filter(Tenant.id.in_(t))

    # Handled like this for a later move to Celery distributed workers

    resp = {"tenants": []}

    for tenant in tenants:
        # Get the last sales order for this tenant, to establish
        # the proper ranging

        last = session.Query(SalesOrder).filter(SalesOrder.tenant == tenant)
        start = last.end
        # Today, the beginning of.
        end = datetime.now(pytz.timezone(DEFAULT_TIMEZONE)).\
            replace(hour=0, minute=0, second=0, microsecond=0)

        # Invoicer is pulled from the configfile and set up above.
        usage = d.usage(start, end, tenant)
        so = SalesOrder()
        so.tenant = tenant
        so.range = (start, end)
        session.add(so)
        # Commit the record before we generate the bill, to mark this as a
        # billed region of data. Avoids race conditions by marking a tenant
        # BEFORE we start to generate the data for it.

        try:
            session.commit()
        except sqlalchemy.exc.IntegrityError:
            session.rollback()
            resp["tenants"].append({
                "id": tenant.id,
                "generated": False,
                "start": start,
                "end": end})
            next
        # Transform the query result into a billable dict.
        # This is non-portable and very much tied to the CSV exporter
        # and will probably result in the CSV exporter being changed.
        billable = billing.build_billable(usage, session)
        generator = invoicer(start, end, config)
        generator.bill(billable)
        generator.close()
        resp["tenants"].append({
            "id": tenant.id,
            "generated": True,
            "start": start,
            "end": end})

    return 200, resp


if __name__ == '__main__':
    pass
