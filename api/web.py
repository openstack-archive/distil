from flask import Flask
app = Flask(__name__)

from artifice.models import Session, usage

conn_string = ('postgresql://%(username)s:%(password)s@' +
               '%(host)s:%(port)s/%(database)s') % conn_dict

Session.configure(bind=create_engine(conn_string))

db = Session()

config = load_config()

current_region = "None" # FIXME
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
@keystone
def retrieve_usage():
    """Retrieves usage for a given tenant ID.
    Tenant ID will be passed in via the query string.
    Expects a keystone auth string in the headers
    and will attempt to perform keystone auth
    """
    tenant = flask.request.params.get("tenant", None)
    if not tenant:
        flask.abort(403, json.dumps({"error":"tenant ID required"})) # Bad request


@app.post("/bill")
@keystone
def make_a_bill():
    """Generates a bill for a given user.
    Expects a JSON dict, with a tenant id and a time range.
    Authentication is expected to be present. 
    """

