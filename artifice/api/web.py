import flask
from flask import Flask, Blueprint
from artifice import interface, database, config, transformers
from artifice.rates import RatesFile
from artifice.models import SalesOrder, Tenant
from artifice.helpers import convert_to
import sqlalchemy
from sqlalchemy import create_engine, func
from sqlalchemy.orm import scoped_session, create_session
from sqlalchemy.pool import NullPool
from datetime import datetime, timedelta
import json

from .helpers import returns_json, json_must


engine = None

Session = None

app = Blueprint("main", __name__)

DEFAULT_TIMEZONE = "Pacific/Auckland"


def get_app(conf):
    actual_app = Flask(__name__)
    actual_app.register_blueprint(app, url_prefix="/")

    config.setup_config(conf)

    global engine
    engine = create_engine(config.main["database_uri"], poolclass=NullPool)

    global Session
    Session = scoped_session(lambda: create_session(bind=engine))

    if config.main.get("timezone"):
        global DEFAULT_TIMEZONE
        DEFAULT_TIMEZONE = config.main["timezone"]

    return actual_app


# Some useful constants
iso_time = "%Y-%m-%dT%H:%M:%S"
iso_date = "%Y-%m-%d"
dawn_of_time = datetime(2014, 4, 1)


def generate_windows(start, end):
    window_size = timedelta(hours=1)
    while start + window_size <= end:
        window_end = start + window_size
        yield start, window_end
        start = window_end


meter_mapping = {
    'state':                {'type': 'virtual_machine',
                             'transformer': transformers.Uptime(),
                             'unit': 'second'},
    'ip.floating':          {'type': 'floating_ip',
                             'transformer': transformers.GaugeMax(),
                             'unit': 'hour'},
    'volume.size':          {'type': 'volume',
                             'transformer': transformers.GaugeMax(),
                             'unit': 'gigabyte'},
    # 'storage.objects.size': {'type': 'object_storage',
    #                          'transformer': transformers.GaugeMax(),
    #                          'unit': 'byte'},
    # TODO: add network usage, when we get the neutron bits for that
    # figured out.
}


def collect_usage(tenant, db, session, resp, end):
    timestamp = datetime.utcnow()
    session.begin(subtransactions=True)

    print 'collect_usage for %s %s' % (tenant.id, tenant.name)
    db_tenant = db.insert_tenant(tenant.id, tenant.name,
                                 tenant.description, timestamp)
    start = db_tenant.last_collected

    if not start:
        print ('failed to find any previous usageentry for this tenant;' +
               'starting at %s' % dawn_of_time)
        start = dawn_of_time
    session.commit()

    for window_start, window_end in generate_windows(start, end):
        session.begin(subtransactions=True)

        try:
            print "%s %s slice %s %s" % (tenant.id, tenant.name, window_start,
                                         window_end)

            for meter_name, meter_info in meter_mapping.items():
                usage = tenant.usage(meter_name, window_start, window_end)
                usage_by_resource = {}

                for u in usage:
                    resource_id = u['resource_id']
                    entries = usage_by_resource.setdefault(resource_id, [])
                    entries.append(u)

                for res, entries in usage_by_resource.items():
                    # apply the transformer.
                    transformed = meter_info['transformer'].transform_usage(
                        meter_name, entries, window_start, window_end)

                    db.insert_resource(tenant.id, res, meter_info['type'],
                                       timestamp)
                    db.insert_usage(tenant.id, res, transformed,
                                    meter_info['unit'],
                                    window_start, window_end, timestamp)

            # update the timestamp for the tenant so we won't examine this
            # timespan again.
            db_tenant.last_collected = window_end
            session.add(db_tenant)

            session.commit()
            resp["tenants"].append(
                {"id": tenant.id,
                 "updated": True,
                 "start": window_start.strftime(iso_time),
                 "end": window_end.strftime(iso_time)
                 }
            )
        except sqlalchemy.exc.IntegrityError:
            # this is fine.
            session.rollback()
            resp["tenants"].append(
                {"id": tenant.id,
                 "updated": False,
                 "error": "Integrity error",
                 "start": window_start.strftime(iso_time),
                 "end": window_end.strftime(iso_time)
                 }
            )
            resp["errors"] += 1


@app.route("collect_usage", methods=["POST"])
def run_usage_collection():
    """
    Adds usage for a given tenant T and resource R.
    Expects to receive a Resource ID, a time range, and a volume.

    The volume will be parsed from JSON as a Decimal object.
    """
    try:

        session = Session()

        artifice = interface.Artifice()
        db = database.Database(session)

        tenants = artifice.tenants

        end = datetime.utcnow().\
            replace(minute=0, second=0, microsecond=0)

        resp = {"tenants": [], "errors": 0}

        for tenant in tenants:
            collect_usage(tenant, db, session, resp, end)

        session.close()
        return json.dumps(resp)

    except Exception as e:
        print 'Exception escaped!', type(e), e
        import traceback
        traceback.print_exc()


def build_tenant_dict(tenant, entries, db):
    """Builds a dict structure for a given tenant.
       -usage: all the usage entries for a given tenant.
        This function assumes all the entries are for the same tenant."""
    tenant_dict = {}

    tenant_dict = {'name': tenant.name, 'tenant_id': tenant.id,
                   'resources': {}}

    for entry in entries:
        service = {'name': entry.service, 'volume': entry.volume,
                   'unit': entry.unit}

        if (entry.resource_id not in tenant_dict['resources']):
            resource = db.get_resource_metadata(entry.resource_id)

            resource['services'] = [service]

            tenant_dict['resources'][entry.resource_id] = resource

        else:
            resource = tenant_dict['resources'][entry.resource_id]
            resource['services'].append(service)

    return tenant_dict


def add_costs_for_tenant(tenant, RatesManager):
    """Adds cost values to services using the given rates manager."""
    tenant_total = 0
    for resource in tenant['resources'].values():
        resource_total = 0
        for service in resource['services']:
            rate = RatesManager.rate(service['name'])
            volume = convert_to(service['volume'],
                                service['unit'],
                                rate['unit'])

            # round to 2dp so in dollars.
            cost = round(volume * rate['rate'], 2)

            service['cost'] = str(cost)
            service['volume'] = str(volume)
            service['unit'] = rate['unit']
            service['rate'] = str(rate['rate'])

            resource_total += cost
        resource['total_cost'] = str(resource_total)
        tenant_total += resource_total
    tenant['total_cost'] = str(tenant_total)

    return tenant


def generate_sales_order(draft, tenant_id):
    session = Session()

    if draft:
        end = datetime.utcnow()
    else:
        # Today, the beginning of.
        end = datetime.utcnow().\
            replace(hour=0, minute=0, second=0, microsecond=0)

    if isinstance(tenant_id, unicode):
        tenant_query = session.query(Tenant).\
            filter(Tenant.id == tenant_id)
        if tenant_query.count() == 0:
            return 400, {"errors": ["No tenant matching ID found."]}
    elif tenant_id is not None:
        return 400, {"missing parameter": {"tenant": "Tenant id."}}

    db = database.Database(session)

    rates = RatesFile(config.rates_config)

    session.begin()
    # Get the last sales order for this tenant, to establish
    # the proper ranging
    start = session.query(func.max(SalesOrder.end).label('end')).\
        filter(SalesOrder.tenant_id == tenant_id).first().end
    if not start:
        start = dawn_of_time
    usage = db.usage(start, end, tenant_id)

    if not draft:
        order = SalesOrder(tenant_id=tenant_id, start=start, end=end)
        session.add(order)

    try:
        # Commit the record before we generate the bill, to mark this as a
        # billed region of data. Avoids race conditions by marking a tenant
        # BEFORE we start to generate the data for it.
        session.commit()

        # Transform the query result into a billable dict.
        tenant_dict = build_tenant_dict(tenant_query[0], usage, db)
        tenant_dict = add_costs_for_tenant(tenant_dict, rates)
        session.close()
        return 200, tenant_dict
    except sqlalchemy.exc.IntegrityError:
        session.rollback()
        session.close()
        return 400, {"id": tenant_id,
                     "error": "IntegrityError, existing sales_order overlap."}


@app.route("sales_order", methods=["POST"])
@json_must()
@returns_json
def run_sales_order_generation():
    tenant_id = flask.request.json.get("tenant", None)
    return generate_sales_order(False, tenant_id)


@app.route("sales_draft", methods=["POST"])
@json_must()
@returns_json
def run_sales_draft_generation():
    tenant_id = flask.request.json.get("tenant", None)
    return generate_sales_order(True, tenant_id)


if __name__ == '__main__':
    pass
