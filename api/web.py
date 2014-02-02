from flask import Flask
app = Flask(__name__)

from artifice.models import Session, usage
from sqlalchemy import type
from decimal import Decimal
from datetime import datetime

conn_string = ('postgresql://%(username)s:%(password)s@' +
               '%(host)s:%(port)s/%(database)s') % conn_dict

Session.configure(bind=create_engine(conn_string))

db = Session()

config = load_config()

iso_time = "%Y-%m-%dT%H:%M:%S"
iso_date = "%Y-%m-%d"

dawn_of_time = "2012-01-01"


current_region = "None" # FIXME

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return json.JSONEncoder.default(self, obj)

def fetch_endpoint(region):
    return config.get("keystone_endpoint")
    # return "http://0.0.0.0:35357/v2.0" # t\/his ought to be in config. #FIXME

def keystone(func):

    admin_token = config.get("admin_token")
    def _perform_keystone(*args, **kwargs):
        headers = flask.request.headers
        if not 'user_id' in headers:
            flask.abort(401) # authentication required
        
        endpoint = fetch_endpoint( current_region )
        keystone = keystoneclient.v2_0.client.Client(token=admin_token,
                endpoint=endpoint)

    return _perform_keystone

@app.get("/usage")
@app.get("/usage/{resource_id}") # also allow for querying by resource ID.
@keystone
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
def add_usage(self):
    """
    Adds usage for a given tenant T.
    Expects to receive a Resource ID, a time range, and a volume.

    The volume will be parsed from JSON as a Decimal object.
    """

    body = json.loads(request.body, parse_float=Decimal)


@app.get("/bill")
@app.get("/bill/{id}")
@keystone
def get_bill():
    """
    Returns either a single bill or a set of the most recent
    bills for a given Tenant.
    """
    pass
    



@app.get("/bill/{bill_id}")
@keystone
def get_bill_by_id(bill_id=None):
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
    bill = usage.Bill()

    # total = 
