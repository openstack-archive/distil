import flask
from flask import Flask, Blueprint
from artifice import interface, database
from artifice.sales_order import RatesFile
from artifice.models import UsageEntry, SalesOrder, Tenant, billing
import sqlalchemy
from sqlalchemy import create_engine, func
from sqlalchemy.orm import scoped_session, create_session
from sqlalchemy.pool import NullPool
from decimal import Decimal
from datetime import datetime
import importlib
import collections
import pytz
import json

from .helpers import returns_json, json_must


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
    # TODO: Try/except block
    invoicer = getattr(importlib.import_module(module), kls)

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


def collect_usage(tenant, db, session, resp, end):
    timestamp = datetime.now()
    db.insert_tenant(tenant.conn['id'], tenant.conn['name'],
                    tenant.conn['description'], timestamp)
    session.begin(subtransactions=True)
    start = session.query(func.max(UsageEntry.end).label('end')).\
        filter(UsageEntry.tenant_id == tenant.conn['id']).first().end
    if not start:
        start = datetime.strptime(dawn_of_time, iso_date)

    usage = tenant.usage(start, end)

    # enter all resources into the db
    db.enter(usage.values(), start, end, timestamp)

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
    db = database.Database(session)

    tenants = artifice.tenants

    end = datetime.now().\
        replace(minute=0, second=0, microsecond=0)

    resp = {"tenants": [], "errors": 0}

    for tenant in tenants:
        collect_usage(tenant, db, session, resp, end)

    session.close()
    return json.dumps(resp)


def generate_sales_order(tenant, session, end, rates):
    db = database.Database(session)

    session.begin()
    # Get the last sales order for this tenant, to establish
    # the proper ranging
    start = session.query(func.max(SalesOrder.end).label('end')).\
        filter(SalesOrder.tenant == tenant).first().end
    if not start:
        start = datetime.strptime(dawn_of_time, iso_date)
    # Invoicer is pulled from the configfile and set up above.
    usage = db.usage(start, end, tenant.id)
    order = SalesOrder(tenant_id=tenant.id, start=start, end=end)
    session.add(order)

    try:
        # Commit the record before we generate the bill, to mark this as a
        # billed region of data. Avoids race conditions by marking a tenant
        # BEFORE we start to generate the data for it.
        session.commit()

        # Transform the query result into a billable dict.
        # This is non-portable and very much tied to the CSV exporter
        # and will probably result in the CSV exporter being changed.
        billable = billing.build_billable(usage, session)
        session.close()
        exporter = invoicer(start, end, config["export_config"], rates)
        exporter.bill(billable)
        exporter.close()
        return {"id": tenant.id,
                "generated": True,
                "start": str(start),
                "end": str(end)}

    except sqlalchemy.exc.IntegrityError:
        session.rollback()
        session.close()
        return {"id": tenant.id,
                "generated": False,
                "start": str(start),
                "end": str(end)}


@app.route("sales_order", methods=["POST"])
@keystone
@json_must()
@returns_json
def run_sales_order_generation():
    session = Session()

    # TODO: ensure cases work as follows:
    # if no body or content type: generate orders for all
    # if no body and json content type: throw 400? Or should this order all?
    # if body, and json, and parsed, but no tenants, throw 400? Or order all.

    # If request has body, content type must be json.
    # else: throw 400
    # if request has body and content type json, body must parse to json
    # else: throw 400

    # if 'tenants' is not None, and not a list, throw a 400 response.

    # if the list is empty, throw 400 and invalid parameter 'list is empty'.
    # Or allow return 200 and resp['tenants'] will just be empty?

    # if list isn't empty, but query produces no results, throw 400?
    # Or allow return 200 and resp['tenants'] will just be empty?

    # any missing cases? Any cases not worth covering?

    # should these checks be here, or in decorators.
    # if in decorators can we make these as parameters for the decorators,
    # to keep them fairly generic, or are these cases too specific?

    tenants = flask.request.json.get("tenants", None)
    tenant_query = session.query(Tenant)

    # Today, the beginning of.
    end = datetime.now().\
        replace(hour=0, minute=0, second=0, microsecond=0)

    if isinstance(tenants, list):
        tenant_query = tenant_query.filter(Tenant.id.in_(tenants))
        if tenant_query.count() == 0:
            # if an explicit list of tenants is passed, and none of them
            # exist in the db, then we consider that an error.
            return 400, {"errors": ["No tenants found from given list."]}
    elif tenants is not None:
        return 400, {"missing parameters": {"tenants": "A list of tenant ids."}}

    # Handled like this for a later move to Celery distributed workers
    resp = {"tenants": []}
    rates = RatesFile(config['export_config'])

    for tenant in tenant_query:
        resp['tenants'].append(generate_sales_order(tenant, session, end, rates))

    return 200, resp


if __name__ == '__main__':
    pass
