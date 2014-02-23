from flask import Flask

from artifice.models import UsageEntry, SalesOrder
from sqlalchemy.orm import scoped_session, create_session
from decimal import Decimal
from datetime import datetime
import collections
import itertools
import pytz

engine = None
# Session.configure(bind=create_engine(conn_string))

db = scoped_session(lambda: create_session(bind=engine))
# db = Session()

config = None

invoicer = None

DEFAULT_TIMEZONE = "Pacific/Auckland"

current_region = "Wellington" # FIXME

def get_app(conf):
    app = Flask(__name__)
    global engine
    engine = create_engine(config["main"]["database_uri"])
    global config
    config = conf

    global invoicer

    module, kls = config["main"]["export_provider"].split(":")
    invoicer = __import__(module, globals(), locals(), [kls])

    if config["main"].get("timezone"):
        global DEFAULT_TIMEZONE
        DEFAULT_TIMEZONE = config["main"]["timezone"]
    
    return app

# invoicer = config["general"]["invoice_handler"]
# module, kls = invoice_type.split(":")
# invoicer = __import__(module, globals(), locals(), [kls])


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
    admin_token = config.get("admin_token")
    def _perform_keystone(*args, **kwargs):
        headers = flask.request.headers
        if not 'user_id' in headers:
            flask.abort(401) # authentication required
        
        endpoint = fetch_endpoint( current_region )
        keystone = keystoneclient.v2_0.client.Client(token=admin_token,
                endpoint=endpoint)

    return _perform_keystone


def must(*args, **kwargs):
    """
    Asserts that a given set of keys are present in the request parameters.
    Also allows for keyword args to handle validation.
    """
    def tester(func):
        def funky(*iargs, **ikwargs):
            body = flask.request.params
            for key in itertools.chain( args, kwargs.keys() ):
                if not key in body:
                    abort(403)
                    return json.dumps({"error": "missing parameter",
                                       "param": key})
            for key, val in kwargs.iteritems():
                input_ = body[key]
                if not val( input_ ):
                    abort(403)
                    return json.dumps({"error": "validation failed",
                                       "param": key}) 
            return func(*iargs, **ikwargs)
        return funky
    return tester


def returns_json(func):
    def jsonify(*args,**kwargs):
        r = func(*args,**kwargs)
        if isinstance(r, dict):
            flask.response.headers["Content-type"] = "application/json"
            return json.dumps(r)
        return r

    return jsonify

def json_must(*args, **kwargs):
    """Implements a simple validation system to allow for the required
       keys to be detected on a given callable."""
    def unpack(func):
        def dejson(*iargs):
            if flask.request.headers["content-encoding"] != "application/json":
                # We throw an exception
                abort(403)
                return json.dumps({"error": "must be in JSON format"})
            body = json.loads( flask.request.body )
            for key in itertools.chain( args, kwargs.keys() ):
                if not key in body:
                    abort(403)
                    return json.dumps({"error": "missing key",
                                       "key": key})
            for key, val in kwargs.iteritems():
                input_ = body[key]
                if not val( input_ ):
                    abort(403)
                    return json.dumps({"error": "validation failed",
                                       "key": key})
            flask.request.body = body
            return func(*args)
        return dejson
    return unpack


@app.get("/usage")
# @app.get("/usage/{resource_id}") # also allow for querying by resource ID.
@keystone
@must("resource_id", "tenant")
def retrieve_usage(resource_id=None):
    """Retrieves usage for a given tenant ID.
    Tenant ID will be passed in via the query string.
    Expects a keystone auth string in the headers
    and will attempt to perform keystone auth
    """
    tenant = flask.request.params.get("tenant", None)
    if not tenant:
        flask.abort(403, json.dumps({"error":"tenant ID required"})) # Bad request
    
    # expect a start and an end timepoint
    
    start = flask.request.params.get("start", None)
    end = flask.request.params.get("end", None)

    if not end:
        end = datetime.now().strftime(iso_date)

    if not start:
        # Hmm. I think this is okay.
        # We just make a date in the dawn of time.
        start = dawn_of_time
    
    start = datetime.strptime(start, iso_date)
    end = datetime.strptime(end, iso_date)
    usages = session.query(usage.Usage)\
            .filter(Usage.tenant_id == tenant)\
            .filter(Usage.time.contained_by(start, end))

    if resource_id:
        usages.filter(usage.Usage.resource_id == resource_id)

    resource = None
    usages = defaultdict(Decimal)
    for usage in usages:
        if usage.resource_id != resource:
            resource = usage.resource_id
        usages[resource] += Decimal(usage.volume)

    # 200 okay
    return ( 200, json.dumps({
        "status":"ok",
        "tenant": tenant,
        "total": usages
    }, cls=DecimalEncoder) ) # Specifically encode decimals appropriate, without float logic


@app.post("/usage")
@keystone
@json_must( tenants=validators.iterable )
@returns_json
def run_usage_collection():
    """
    Adds usage for a given tenant T and resource R.
    Expects to receive a Resource ID, a time range, and a volume.

    The volume will be parsed from JSON as a Decimal object.
    """
    
    # TODO
    artifice = interface.Artifice( config["artifice"] )
    start = datetime.strptime(start, iso_date)
    end = datetime.strptime(end, iso_date)

    d = Database(session)
    
    # Handled in a loop here for later movement to a Celery-based backend
    # system

    body = flask.request.body
    tenants = session.query(Tenants).filter(Tenants.active)
    if body["tenants"]:
        tenants.filter(Tenants.id.in_(body["tenants"]))
    
    resp = {
            "tenants": [],
            "errors": 0
           }
    for tenant in tenants:
        
        start = session.query(func.max(UsageEntry.end).label("end")).\
                filter(UsageEntry.tenant == tenant).end

        end = datetime.now(pytz.timezone( DEFAULT_TIMEZONE )) \
            .replace(minute=0, second=0, microsecond=0)
        
        usage = artifice.tenant(tenant.id).usage(start, end)
        # .values() returns a tuple of lists of entries of artifice Resource models
        # enter expects a list of direct resource models.
        # So, unwind the list.
        for resource in usage.values():
            d.enter( t , resource )
        try:
            session.commit()
            resp["tenants"].append(
                    {"id": tenant.id,
                     "updated": True,
                     "start": start.strftime(iso_time),
                     "end":   end.strftime(iso_time)
                    }
            )
        except sqlalchemy.exc.IntegrityError:
            # this is fine.
            resp["tenants"].append(
                    {"id": tenant.id,
                     "updated": False,
                     "error": "Integrity error",
                     "start": start.strftime(iso_time),
                     "end":   end.strftime(iso_time)
                    }
            )
            resp["errors"] += 1
    return resp

@app.post("/sales_order")
@keystone
@json_must("tenants")
def run_sales_order_generation():
    
    # get
    start = datetime.strptime(start, iso_date)
    end = datetime.strptime(end, iso_date)
    d = Database(session)
    current_tenant = None

    body = json.loads(request.body)

    t = body.get( "tenants", None )
    tenants = session.query(Tenant).filter(Tenant.active == True)
    if t:
        t.filter( Tenants.id.in_(t) )
    
    # Handled like this for a later move to Celery distributed workers
    
    resp = {
            "tenants": []
            }
    for tenant in tenants:
        # Get the last sales order for this tenant, to establish
        # the proper ranging

        last = session.Query(SalesOrders).filter(SalesOrders.tenant == tenant)
        start = last.end
        # Today, the beginning of.
        end = datetime.now(pytz.timezone( DEFAULT_TIMEZONE )) \
            .replace(hour=0, minute=0, second=0, microsecond=0)

        # Invoicer is pulled from the configfile and set up above.
        usage = d.usage(start, end, tenant)
        so = SalesOrder()
        so.tenant = tenant
        so.range = (start, end)
        session.add(so)
        # Commit the record before we generate the bill, to mark this as a 
        # billed region of data. Avoids race conditions by marking a tenant BEFORE
        # we start to generate the data for it.
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
        generator = invoicer(billable, start, end, config)
        generator.bill()
        generator.close()
        resp["tenants"].append({
                "id": tenant.id,
                "generated": True,
                "start": start,
                "end": end})

    status(201) # created
    response.headers[ "Content-type" ] = "application/json"
    return json.dumps( resp )


@app.get("/bills/{id}")
@keystone
@must("tenant", "start", "end")
def get_bill(id_):
    """
    Returns either a single bill or a set of the most recent
    bills for a given Tenant.
    """

    # TODO: Put these into an input validator instead
    try:
        start = datetime.strptime(request.params["start"], date_iso)
    except:
        abort(
            403, 
            json.dumps(
                {"status":"error", 
                 "error": "start date is not ISO-compliant"})
        )
    try:
        end = datetime.strptime(request.params["end"], date_iso)
    except:
        abort(
            403, 
            json.dumps(
                {"status":"error", 
                 "error": "end date is not ISO-compliant"})
        )

    try:
        bill = BillInterface(session).get(id_)
    except:
        abort(404)

    if not bill:
        abort(404)

    resp = {"status": "ok",
            "bill": [],
            "total": str(bill.total),
            "tenant": bill.tenant_id
           }

    for resource in billed:
        resp["bill"].append({
            'resource_id': bill.resource_id,
            'volume': str( bill.volume ),
            'rate': str( bill.rate ),
            # 'metadata':  # TODO: This will be filled in with extra data
        })
    
    return (200, json.dumps(resp))
    
@app.post("/usage/current")
@keystone
@must("tenant_id")
def get_current_usage():
    """
    Is intended to return a running total of the current billing periods'
    dataset. Performs a Rate transformer on each transformed datapoint and 
    returns the result.

    TODO: Implement
    """
    pass

@app.post("/bill")
@keystone
def make_a_bill():
    """Generates a bill for a given user.
    Expects a JSON dict, with a tenant id and a time range.
    Authentication is expected to be present. 
    This *will* interact with the ERP plugin and perform a bill-generation
    cycle.
    """
    
    body = json.loads(request.body)
    tenant = body.get("tenant", None)
    if not tenant:
        return abort(403) # bad request
    
    start = body.get("start", None)
    end = body.get("end", None)
    if not start or not end:
        return abort(403) # All three *must* be defined
    

    bill = BillInterface(session)
    thebill = bill.generate(body["tenant_id"], start, end)
    # assumes the bill is saved

    if not thebill.is_saved:
        # raise an error
        abort(500)
    
    resp = {"status":"created",
            "id": thebill.id,
            "contents": [],
            "total": None
           }
    for resource in thebill.resources:
        total += Decimal(billed.total)
        resp["contents"].append({
            'resource_id': bill.resource_id,
            'volume': str( bill.volume ),
            'rate': str( bill.rate ),
            # 'metadata':  # TODO: This will be filled in with extra data
        })
    
    resp["total"] = thebill.total
    return (201, json.dumps(resp))


if __name__ == '__main__':
    pass
