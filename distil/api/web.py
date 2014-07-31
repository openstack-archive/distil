import flask
from flask import Flask, Blueprint
from distil import database, config
from distil.constants import iso_time, iso_date, dawn_of_time
from distil.transformers import active_transformers
from distil.rates import RatesFile
from distil.models import SalesOrder, _Last_Run
from distil.helpers import convert_to
from distil.interface import Interface, timed
from sqlalchemy import create_engine, func
from sqlalchemy.orm import scoped_session, create_session
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import IntegrityError, OperationalError
from datetime import datetime, timedelta
import json
import logging as log

from .helpers import returns_json, json_must, validate_tenant_id


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

    log.basicConfig(filename=config.main["log_file"],
                    level=log.INFO,
                    format='%(asctime)s %(message)s')
    log.info("Billing API started.")

    return actual_app


def generate_windows(start, end):
    """Generator for 1 hour windows in a given range."""
    window_size = timedelta(hours=1)
    while start + window_size <= end:
        window_end = start + window_size
        yield start, window_end
        start = window_end


def collect_usage(tenant, db, session, resp, end):
    """Collects usage for a given tenant from when they were last collected,
       up to the given end, and breaks the range into one hour windows."""
    run_once = False
    timestamp = datetime.utcnow()
    session.begin(subtransactions=True)

    log.info('collect_usage for %s %s' % (tenant.id, tenant.name))

    db_tenant = db.insert_tenant(tenant.id, tenant.name,
                                 tenant.description, timestamp)
    start = db_tenant.last_collected
    session.commit()

    trust_sources = set(config.main.get('trust_sources', []))

    for window_start, window_end in generate_windows(start, end):
        with timed("new transaction"):
            session.begin(subtransactions=True)

        try:
            log.info("%s %s slice %s %s" % (tenant.id, tenant.name,
                                            window_start, window_end))

            mappings = config.collection['meter_mappings']

            for meter_name, meter_info in mappings.items():
                usage = tenant.usage(meter_name, window_start, window_end)
                usage_by_resource = {}

                transformer = active_transformers[meter_info['transformer']]()

                with timed("filter and group by resource"):
                    for u in usage:
                        # the user can make their own samples, including those
                        # that would collide with what we care about for
                        # billing.
                        # if we have a list of trust sources configured, then
                        # discard everything not matching.
                        if trust_sources and u['source'] not in trust_sources:
                            log.warning('ignoring untrusted usage sample ' +
                                        'from source `%s`' % u['source'])
                            continue

                        resource_id = u['resource_id']
                        entries = usage_by_resource.setdefault(resource_id, [])
                        entries.append(u)

                with timed("apply transformer + insert"):
                    for res, entries in usage_by_resource.items():
                        # apply the transformer.
                        transformed = transformer.transform_usage(
                            meter_name, entries, window_start, window_end)

                        if transformed:
                            if meter_info.get('transform_info', False):
                                if 'res_id_template' in meter_info:
                                    res = (meter_info['res_id_template'] % res)

                                db.insert_resource(tenant.id, res,
                                                   meter_info['type'],
                                                   timestamp, entries[-1],
                                                   True)
                                db.insert_usage(tenant.id, res, transformed,
                                                meter_info['unit'],
                                                window_start, window_end,
                                                timestamp)

                            else:
                                db.insert_resource(tenant.id, res,
                                                   meter_info['type'],
                                                   timestamp, entries[-1],
                                                   False)
                                db.insert_usage(tenant.id, res, transformed,
                                                meter_info['unit'],
                                                window_start, window_end,
                                                timestamp)

            with timed("commit insert"):
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
            run_once = True
        except (IntegrityError, OperationalError):
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
            log.warning("IntegrityError for %s %s in window: %s - %s " %
                        (tenant.name, tenant.id,
                         window_start.strftime(iso_time),
                         window_end.strftime(iso_time)))
            return run_once
    return run_once


@app.route("collect_usage", methods=["POST"])
def run_usage_collection():
    """Run usage collection on all tenants present in Keystone."""
    try:
        log.info("Usage collection run started.")

        session = Session()

        interface = Interface()
        db = database.Database(session)

        end = datetime.utcnow().\
            replace(minute=0, second=0, microsecond=0)

        tenants = interface.tenants

        resp = {"tenants": [], "errors": 0}
        run_once = False

        for tenant in tenants:
            if collect_usage(tenant, db, session, resp, end):
                run_once = True

        if(run_once):
            session.begin()
            last_run = session.query(_Last_Run)
            if last_run.count() == 0:
                last_run = _Last_Run(last_run=end)
                session.add(last_run)
                session.commit()
            else:
                last_run[0].last_run = end
                session.commit()

        session.close()
        log.info("Usage collection run complete.")
        return json.dumps(resp)

    except Exception as e:
        import traceback
        trace = traceback.format_exc()
        log.critical('Exception escaped! %s \nTrace: \n%s' % (e, trace))


def build_tenant_dict(tenant, entries, db):
    """Builds a dict structure for a given tenant."""
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
            try:
                rate = RatesManager.rate(service['name'])
            except KeyError:
                # no rate exists for this service
                service['cost'] = "0"
                service['volume'] = "unknown unit conversion"
                service['unit'] = "unknown"
                service['rate'] = "missing rate"
                continue

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


def generate_sales_order(draft, tenant_id, end):
    """Generates a sales order dict, and unless draft is true,
       creates a database entry for sales_order."""
    session = Session()
    db = database.Database(session)

    valid_tenant = validate_tenant_id(tenant_id, session)
    if isinstance(valid_tenant, tuple):
        return valid_tenant

    rates = RatesFile(config.rates_config)

    # Get the last sales order for this tenant, to establish
    # the proper ranging
    start = session.query(func.max(SalesOrder.end).label('end')).\
        filter(SalesOrder.tenant_id == tenant_id).first().end
    if not start:
        start = dawn_of_time

    # these coditionals need work, also some way to
    # ensure all given timedate values are in UTC?
    if end <= start:
        return 400, {"errors": ["end date must be greater than " +
                                "the end of the last sales order range."]}
    if end > datetime.utcnow():
        return 400, {"errors": ["end date cannot be a future date."]}

    usage = db.usage(start, end, tenant_id)

    session.begin()
    if not draft:
        order = SalesOrder(tenant_id=tenant_id, start=start, end=end)
        session.add(order)

    try:
        # Commit the record before we generate the bill, to mark this as a
        # billed region of data. Avoids race conditions by marking a tenant
        # BEFORE we start to generate the data for it.
        session.commit()

        # Transform the query result into a billable dict.
        tenant_dict = build_tenant_dict(valid_tenant, usage, db)
        tenant_dict = add_costs_for_tenant(tenant_dict, rates)

        # add sales order range:
        tenant_dict['start'] = str(start)
        tenant_dict['end'] = str(end)
        session.close()
        if not draft:
            log.info("Sales Order #%s Generated for %s in range: %s - %s" %
                     (order.id, tenant_id, start, end))
        return 200, tenant_dict
    except (IntegrityError, OperationalError):
        session.rollback()
        session.close()
        log.warning("IntegrityError creating sales-order for " +
                    "%s %s in range: %s - %s " %
                    (valid_tenant.name, valid_tenant.id, start, end))
        return 400, {"id": tenant_id,
                     "error": "IntegrityError, existing sales_order overlap."}


def regenerate_sales_order(tenant_id, target):
    """Finds a sales order entry nearest to the target,
       and returns a salesorder dict based on the entry."""
    session = Session()
    db = database.Database(session)
    rates = RatesFile(config.rates_config)

    valid_tenant = validate_tenant_id(tenant_id, session)
    if isinstance(valid_tenant, tuple):
        return valid_tenant

    try:
        sales_order = db.get_sales_orders(tenant_id, target, target)[0]
    except IndexError:
        return 400, {"errors": ["Given date not in existing sales orders."]}

    usage = db.usage(sales_order.start, sales_order.end, tenant_id)

    # Transform the query result into a billable dict.
    tenant_dict = build_tenant_dict(valid_tenant, usage, db)
    tenant_dict = add_costs_for_tenant(tenant_dict, rates)

    # add sales order range:
    tenant_dict['start'] = str(sales_order.start)
    tenant_dict['end'] = str(sales_order.end)

    return 200, tenant_dict


def regenerate_sales_order_range(tenant_id, start, end):
    """For all sales orders in a given range, generate sales order dicts,
       and return them."""
    session = Session()
    db = database.Database(session)
    rates = RatesFile(config.rates_config)

    valid_tenant = validate_tenant_id(tenant_id, session)
    if isinstance(valid_tenant, tuple):
        return valid_tenant

    sales_orders = db.get_sales_orders(tenant_id, start, end)

    tenants = []
    for sales_order in sales_orders:
        usage = db.usage(sales_order.start, sales_order.end, tenant_id)

        # Transform the query result into a billable dict.
        tenant_dict = build_tenant_dict(valid_tenant, usage, db)
        tenant_dict = add_costs_for_tenant(tenant_dict, rates)

        # add sales order range:
        tenant_dict['start'] = str(sales_order.start)
        tenant_dict['end'] = str(sales_order.end)

        tenants.append(tenant_dict)

    return 200, tenants


@app.route("sales_order", methods=["POST"])
@json_must()
@returns_json
def run_sales_order_generation():
    """Generates a sales order for the given tenant.
       -end: a given end date, or uses default"""
    tenant_id = flask.request.json.get("tenant", None)
    end = flask.request.json.get("end", None)
    if not end:
        # Today, the beginning of.
        end = datetime.utcnow().\
            replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        try:
            end = datetime.strptime(end, iso_date)
        except ValueError:
            return 400, {"errors": ["'end' date given needs to be in format:" +
                                    " y-m-d"]}

    return generate_sales_order(False, tenant_id, end)


@app.route("sales_draft", methods=["POST"])
@json_must()
@returns_json
def run_sales_draft_generation():
    """Generates a sales draft for the given tenant.
       -end: a given end datetime, or uses default"""
    tenant_id = flask.request.json.get("tenant", None)
    end = flask.request.json.get("end", None)

    if not end:
        end = datetime.utcnow()
    else:
        try:
            end = datetime.strptime(end, iso_date)
        except ValueError:
            try:
                end = datetime.strptime(end, iso_time)
            except ValueError:
                return 400, {
                    "errors": ["'end' date given needs to be in format: " +
                               "y-m-d, or y-m-dTH:M:S"]}

    return generate_sales_order(True, tenant_id, end)


@app.route("sales_historic", methods=["POST"])
@json_must()
@returns_json
def run_sales_historic_generation():
    """Returns the sales order that intersects with the given target date.
       -target: a given target date"""
    tenant_id = flask.request.json.get("tenant", None)
    target = flask.request.json.get("date", None)

    if target is not None:
        try:
            target = datetime.strptime(target, iso_date)
        except ValueError:
            return 400, {"errors": ["date given needs to be in format: " +
                                    "y-m-d"]}
    else:
        return 400, {"missing parameter": {"date": "target date in format: " +
                                           "y-m-d"}}

    return regenerate_sales_order(tenant_id, target)


@app.route("sales_range", methods=["POST"])
@json_must()
@returns_json
def run_sales_historic_range_generation():
    """Returns the sales orders that intersect with the given date range.
       -start: a given start for the range.
       -end: a given end for the range, defaults to now."""
    tenant_id = flask.request.json.get("tenant", None)
    start = flask.request.json.get("start", None)
    end = flask.request.json.get("end", None)

    try:
        if start is not None:
            start = datetime.strptime(start, iso_date)
        else:
            return 400, {"missing parameter": {"start": "start date" +
                                               " in format: y-m-d"}}
        if end is not None:
                end = datetime.strptime(end, iso_date)
        else:
            end = datetime.utcnow()
    except ValueError:
            return 400, {"errors": ["dates given need to be in format: " +
                                    "y-m-d"]}

    return regenerate_sales_order_range(tenant_id, start, end)


if __name__ == '__main__':
    pass
