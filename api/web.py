from flask import Flask
app = Flask(__name__)

from artifice.models import Session, usage
from artifice.models import billing
from sqlalchemy import type
from decimal import Decimal
from datetime import datetime

conn_string = ('postgresql://%(username)s:%(password)s@' +
               '%(host)s:%(port)s/%(database)s') % conn_dict

Session.configure(bind=create_engine(conn_string))

db = Session()

config = load_config()


invoicer = config["general"]["invoice_handler"]
module, kls = invoice_type.split(":")
invoicer = __import__(module, globals(), locals(), [kls])


# Some useful constants

iso_time = "%Y-%m-%dT%H:%M:%S"
iso_date = "%Y-%m-%d"

dawn_of_time = "2012-01-01"


current_region = "None" # FIXME

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

# TODO: fill me in
def must(*args):
    return lambda(func): func

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
@must("start", "end", "tenants")
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

    for tenant in flask.request.params.get("tenant", None):
        t = artifice.tenant(tenant)
        usage = t.usage(start, end)
        # .values() returns a tuple of lists of entries of artifice Resource models
        # enter expects a list of direct resource models.
        # So, unwind the list.
        for resource in usage.values():
            d.enter( t , resource )
    session.commit()
    

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

    for tenant in tenants:
        usage = d.usage(start, end, tenant)
        billable = billing.build_billable(usage, session)
        generator = invoicer(billable, start, end, config)
        generator.bill()
        generator.close()


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
