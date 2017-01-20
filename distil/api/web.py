# Copyright (C) 2014 Catalyst IT Ltd
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import flask
import hashlib
import re
from distil.NoPickle import NoPickle
from flask import Flask, Blueprint
from distil import database, config
from distil.constants import iso_time, iso_date, dawn_of_time
from distil.transformers import active_transformers as transformers
from distil.rates import RatesFile
from distil.models import _Last_Run
from distil.helpers import convert_to, reset_cache
from distil.interface import Interface, timed
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, create_session
from sqlalchemy.pool import NullPool
from sqlalchemy.exc import IntegrityError, OperationalError
# Fix the the multithread issue when using strptime, based on this link:
# stackoverflow.com/questions/2427240/thread-safe-equivalent-to-pythons-time-strptime   # noqa
import _strptime
from datetime import datetime, timedelta
from decimal import Decimal
import json
import logging
from keystonemiddleware import auth_token

from .helpers import returns_json, json_must, validate_tenant_id, require_admin
from .helpers import require_admin_or_owner
from urlparse import urlparse


engine = None

Session = None

memcache = None

app = Blueprint("main", __name__)

DEFAULT_TIMEZONE = "Pacific/Auckland"

RATES = None

# NOTE(adriant): Doing this to avoid a unit test failure:
log = logging

# Double confirm by:
# http://blog.namis.me/2012/02/14/python-strptime-is-not-thread-safe/
dumy_call = datetime.strptime("2011-04-05 18:40:58.525996",
                              "%Y-%m-%d %H:%M:%S.%f")

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

    global log
    log = logging.getLogger("Distil_Log")
    log.propagate = False
    file_hdlr = logging.FileHandler(config.main["log_file"])
    formatter = logging.Formatter(
        '(%(asctime)s) - %(levelname)s - %(message)s')
    file_hdlr.setFormatter(formatter)
    log.addHandler(file_hdlr)
    log.setLevel(logging.INFO)

    log.info("Billing API started.")

    setup_memcache()

    # if configured to authenticate clients, then wrap the
    # wsgi app in the keystone middleware.
    if config.auth.get('authenticate_clients'):
        identity_url = urlparse(config.auth['identity_url'])
        conf = {
            'admin_user': config.auth['username'],
            'admin_password': config.auth['password'],
            'admin_tenant_name': config.auth['default_tenant'],
            'auth_host': identity_url.hostname,
            'auth_port': identity_url.port,
            'auth_protocol': identity_url.scheme
        }
        actual_app = auth_token.AuthProtocol(actual_app, conf)

    return actual_app


def setup_memcache():
    if config.memcache['enabled']:
        log.info("Memcache enabled.")
        import memcache as memcached
        global memcache
        memcache = memcached.Client(config.memcache['addresses'],
                                    pickler=NoPickle, unpickler=NoPickle)
    else:
        log.info("Memcache disabled.")


@app.route("last_collected", methods=["GET"])
@returns_json
@require_admin
def get_last_collected():
    """Simple call to get timestamp for the last collection run."""
    session = Session()
    session.begin()
    last_run = session.query(_Last_Run)
    if last_run.count() == 0:
        last_collected = dawn_of_time
    else:
        last_collected = last_run[0].last_run
    session.close()
    return 200, {'last_collected': str(last_collected)}


def generate_windows(start, end):
    """Generator for 1 hour windows in a given range."""
    window_size = timedelta(hours=1)
    while start + window_size <= end:
        window_end = start + window_size
        yield start, window_end
        start = window_end


def filter_and_group(usage, usage_by_resource):
    with timed("filter and group by resource"):
        trust_sources = set(config.main.get('trust_sources', []))
        for u in usage:
            # the user can make their own samples, including those
            # that would collide with what we care about for
            # billing.
            # if we have a list of trust sources configured, then
            # discard everything not matching.
            # NOTE(flwang): When posting samples by ceilometer REST API, it
            # will use the format <tenant_id>:<source_name_from_user>
            # so we need to use a regex to recognize it.
            if (trust_sources and
                all([not re.match(source, u['source'])
                     for source in trust_sources]) == True):
                log.warning('Ignoring untrusted usage sample ' +
                            'from source `%s`' % u['source'])
                continue

            resource_id = u['resource_id']
            entries = usage_by_resource.setdefault(resource_id, [])
            entries.append(u)


def transform_and_insert(tenant, usage_by_resource, transformer, service,
                         mapping, window_start, window_end,
                         db, timestamp):
    with timed("apply transformer + insert"):
        for res, entries in usage_by_resource.items():
            # apply the transformer.
            transformed = transformer.transform_usage(
                service, entries, window_start, window_end)

            if transformed:
                res = mapping.get('res_id_template', '%s') % res

                md_def = mapping['metadata']

                db.insert_resource(tenant.id, res, mapping['type'],
                                   timestamp, entries[-1], md_def)
                db.insert_usage(tenant.id, res, transformed,
                                mapping['unit'], window_start,
                                window_end, timestamp)


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

    max_windows = config.collection.get('max_windows_per_cycle', 0)
    windows = generate_windows(start, end)

    if max_windows:
        windows = list(windows)[:max_windows]

    for window_start, window_end in windows:
        try:
            with session.begin(subtransactions=True):
                log.info("%s %s slice %s %s" % (tenant.id, tenant.name,
                                                window_start, window_end))

                mappings = config.collection['meter_mappings']

                for mapping in mappings:
                    usage = tenant.usage(mapping['meter'], window_start, window_end)
                    usage_by_resource = {}

                    transformer = transformers[mapping['transformer']]()

                    filter_and_group(usage, usage_by_resource)

                    if 'service' in mapping:
                        service = mapping['service']
                    else:
                        service = mapping['meter']

                    transform_and_insert(tenant, usage_by_resource,
                                         transformer, service, mapping,
                                         window_start, window_end, db,
                                         timestamp)

                db_tenant.last_collected = window_end
                session.add(db_tenant)

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
@require_admin
def run_usage_collection():
    """Run usage collection on all tenants present in Keystone."""
    try:
        log.info("Usage collection run started.")

        session = Session()

        interface = Interface()

        reset_cache()

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


def make_serializable(obj):
    if isinstance(obj, list):
        return [make_serializable(x) for x in obj]
    if isinstance(obj, dict):
        return {make_serializable(k):make_serializable(v) for k,v in obj.items()}

    if isinstance(obj, Decimal):
        return str(obj)

    return obj


@app.route("get_usage", methods=["GET"])
@require_admin_or_owner
@returns_json
def get_usage():
    """
    Get raw aggregated usage for a tenant, in a given timespan.
        - No rates are applied.
        - No conversion from collection unit to billing unit
        - No rounding
    """
    tenant_id = flask.request.args.get('tenant')
    start = flask.request.args.get('start')
    end = flask.request.args.get('end')

    log.info("get_usage for %s %s %s" % (tenant_id, start, end))

    try:
        start_dt = datetime.strptime(end, iso_time)
    except ValueError:
        return 400, {'error': 'Invalid start datetime'}

    try:
        end_dt = datetime.strptime(end, iso_time)
    except ValueError:
        return 400, {'error': 'Invalid end datetime'}

    if end_dt < start_dt:
        return 400, {'error': 'End must be after start'}

    session = Session()
    db = database.Database(session)

    valid_tenant = validate_tenant_id(tenant_id, session)
    if isinstance(valid_tenant, tuple):
        return valid_tenant

    log.info("parameter validation ok")

    if memcache is not None:
        key = make_key("raw_usage", tenant_id, start, end)

        data = memcache.get(key)
        if data is not None:
            log.info("Returning memcache raw data for %s in range: %s - %s" %
                     (tenant_id, start, end))
            return 200, data

    log.info("Calculating raw data for %s in range: %s - %s" %
             (tenant_id, start, end))

    # aggregate usage
    usage = db.usage(start, end, tenant_id)
    tenant_dict = build_tenant_dict(valid_tenant, usage, db)

    response_json = json.dumps({'usage': make_serializable(tenant_dict)})

    if memcache is not None:
        memcache.set(key, response_json)

    return 200, response_json


@app.route("get_rated", methods=["GET"])
@require_admin_or_owner
@returns_json
def get_rated():
    """
    Get rated aggregated usage for a tenant, in a given timespan.
    Rates used are those at the 'start' of the timespan.
       -tenant_id: tenant to get data for.
       -start: a given start for the range.
       -end: a given end for the range, defaults to now.
    """
    tenant_id = flask.request.args.get('tenant', None)
    start = flask.request.args.get('start', None)
    end = flask.request.args.get('end', None)

    try:
        if start is not None:
            try:
                start = datetime.strptime(start, iso_date)
            except ValueError:
                start = datetime.strptime(start, iso_time)
        else:
            return 400, {"missing parameter": {"start": "start date" +
                                               " in format: y-m-d"}}
        if not end:
            end = datetime.utcnow()
        else:
            try:
                end = datetime.strptime(end, iso_date)
            except ValueError:
                end = datetime.strptime(end, iso_time)
    except ValueError:
            return 400, {
                "errors": ["'end' date given needs to be in format: " +
                           "y-m-d, or y-m-dTH:M:S"]}

    if end <= start:
        return 400, {"errors": ["end date must be greater than start."]}

    session = Session()

    valid_tenant = validate_tenant_id(tenant_id, session)
    if isinstance(valid_tenant, tuple):
        return valid_tenant

    if memcache is not None:
        key = make_key("rated_usage", valid_tenant.id, start, end)

        data = memcache.get(key)
        if data is not None:
            log.info("Returning memcache rated data for %s in range: %s - %s" %
                     (valid_tenant.id, start, end))
            return 200, data

    log.info("Calculating rated data for %s in range: %s - %s" %
             (valid_tenant.id, start, end))

    tenant_dict = calculate_rated_data(valid_tenant, start, end, session)

    response_json = json.dumps({'usage': tenant_dict})

    if memcache is not None:
        memcache.set(key, response_json)

    return 200, response_json


def make_key(api_call, tenant_id, start, end):
    call_info = [config.memcache['key_prefix'], api_call,
                 tenant_id, str(start), str(end)]
    return hashlib.sha256(str(call_info)).hexdigest()


def build_tenant_dict(tenant, entries, db):
    """Builds a dict structure for a given tenant."""
    tenant_dict = {'name': tenant.name, 'tenant_id': tenant.id}

    all_resource_ids = {entry.resource_id for entry in entries}
    tenant_dict['resources'] = db.get_resources(all_resource_ids)

    for entry in entries:
        service = {'name': entry.service, 'volume': entry.volume,
                'unit': entry.unit}

        resource = tenant_dict['resources'][entry.resource_id]
        service_list = resource.setdefault('services', [])
        service_list.append(service)

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


def calculate_rated_data(tenant, start, end, session):
    """Calculate a rated data dict from the given range."""

    db = database.Database(session)

    global RATES
    if not RATES:
        RATES = RatesFile(config.rates_config)

    usage = db.usage(start, end, tenant.id)

    # Transform the query result into a billable dict.
    tenant_dict = build_tenant_dict(tenant, usage, db)
    tenant_dict = add_costs_for_tenant(tenant_dict, RATES)

    # add sales order range:
    tenant_dict['start'] = str(start)
    tenant_dict['end'] = str(end)

    return tenant_dict


if __name__ == '__main__':
    pass
