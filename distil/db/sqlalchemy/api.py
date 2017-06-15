# Copyright 2014 Catalyst IT Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Implementation of SQLAlchemy backend."""

import contextlib
from datetime import datetime
import json
import sys
import threading

from oslo_config import cfg
from oslo_db import exception as db_exception
from oslo_db.sqlalchemy import session as db_session
from oslo_log import log as logging
from retrying import retry
import six
import sqlalchemy as sa
from sqlalchemy import func

from distil.db.sqlalchemy import models as m
from distil.db.sqlalchemy.models import ProjectLock
from distil.db.sqlalchemy.models import Resource
from distil.db.sqlalchemy.models import Tenant
from distil.db.sqlalchemy.models import UsageEntry
from distil import exceptions

LOG = logging.getLogger(__name__)

CONF = cfg.CONF

_FACADE = None
_LOCK = threading.Lock()


def _create_facade_lazily():
    global _LOCK, _FACADE

    if _FACADE is None:
        with _LOCK:
            if _FACADE is None:
                _FACADE = db_session.EngineFacade.from_config(CONF,
                                                              sqlite_fk=True)
    return _FACADE


def get_engine():
    facade = _create_facade_lazily()
    return facade.get_engine()


def get_session(**kwargs):
    facade = _create_facade_lazily()
    return facade.get_session(**kwargs)


def cleanup():
    global _FACADE
    _FACADE = None


def get_backend():
    return sys.modules[__name__]


def setup_db():
    try:
        engine = get_engine()
        m.Tenant.metadata.create_all(engine)
    except sa.exc.OperationalError as e:
        LOG.exception("Database registration exception: %s", e)
        return False
    return True


def drop_db():
    try:
        engine = get_engine()
        m.Tenant.metadata.drop_all(engine)
    except Exception as e:
        LOG.exception("Database shutdown exception: %s", e)
        return False
    return True


def model_query(model, context, session=None, project_only=True):
    """Query helper.

    :param model: base model to query
    :param context: context to query under
    :param project_only: if present and context is user-type, then restrict
            query to match the context's tenant_id.
    """
    session = session or get_session()
    query = session.query(model)
    if project_only and not context.is_admin:
        query = query.filter_by(tenant_id=context.tenant_id)
    return query


def apply_filters(query, model, **filters):
    """Apply filter for db query.

    Sample of filters:
    {
        'key1': {'op': 'in', 'value': [1, 2]},
        'key2': {'op': 'lt', 'value': 10},
        'key3': 'value'
    }
    """
    filter_dict = {}

    for key, criteria in filters.items():
        column_attr = getattr(model, key)
        if isinstance(criteria, dict):
            if criteria['op'] == 'in':
                query = query.filter(column_attr.in_(criteria['value']))
            elif criteria['op'] == 'nin':
                query = query.filter(~column_attr.in_(criteria['value']))
            elif criteria['op'] == 'neq':
                query = query.filter(column_attr != criteria['value'])
            elif criteria['op'] == 'gt':
                query = query.filter(column_attr > criteria['value'])
            elif criteria['op'] == 'gte':
                query = query.filter(column_attr >= criteria['value'])
            elif criteria['op'] == 'lt':
                query = query.filter(column_attr < criteria['value'])
            elif criteria['op'] == 'lte':
                query = query.filter(column_attr <= criteria['value'])
            elif criteria['op'] == 'eq':
                query = query.filter(column_attr == criteria['value'])
            elif criteria['op'] == 'like':
                like_pattern = '%{0}%'.format(criteria['value'])
                query = query.filter(column_attr.like(like_pattern))
        else:
            filter_dict[key] = criteria

    if filter_dict:
        query = query.filter_by(**filter_dict)

    return query


def _project_get(session, project_id):
    return session.query(Tenant).filter_by(id=project_id).first()


def project_add(values, last_collect=None):
    session = get_session()
    project = _project_get(session, values['id'])

    if not project:
        if not last_collect:
            last_collect = datetime.strptime(
                CONF.collector.dawn_of_time,
                "%Y-%m-%d %H:%M:%S"
            )

        project = Tenant(id=values['id'], name=values['name'],
                         info=values['description'], created=datetime.utcnow(),
                         last_collected=last_collect)

        try:
            project.save(session=session)
        except db_exception.DBDuplicateEntry as e:
            raise exceptions.DuplicateException(
                "Duplicate entry for Tenant: %s" % e.columns
            )

    return project


def project_get_all(**filters):
    session = get_session()
    query = session.query(Tenant)
    query = apply_filters(query, Tenant, **filters)

    return query.all()


def project_get(project_id):
    session = get_session()
    query = session.query(Tenant)
    query = query.filter(Tenant.id == project_id)
    try:
        return query.one()
    except Exception:
        raise exceptions.NotFoundException(
            "Project %s not found." % project_id
        )


def get_last_collect(project_ids):
    session = get_session()
    query = session.query(
        func.min(Tenant.last_collected).label("last_collected")
    )
    query = query.filter(Tenant.id.in_(project_ids))

    return query.one()


def usage_get(project_id, start, end):
    session = get_session()
    query = session.query(UsageEntry.tenant_id,
                          UsageEntry.resource_id,
                          UsageEntry.service,
                          UsageEntry.unit,
                          func.sum(UsageEntry.volume).label("volume"))

    query = (query.filter(UsageEntry.start >= start,
                          UsageEntry.end <= end).
             filter(UsageEntry.tenant_id == project_id).
             group_by(UsageEntry.tenant_id, UsageEntry.resource_id,
                      UsageEntry.service, UsageEntry.unit))
    result = []
    # NOTE(flwang): With group_by and func.sum, the query result is a list of
    # array, which is hard to be consumed. So Here we're using a named tuple
    # so that it can be easier to use.
    for entry in query.all():
        ue = UsageEntry()
        ue.tenant_id = entry[0]
        ue.resource_id = entry[1]
        ue.service = entry[2]
        ue.unit = entry[3]
        ue.volume = entry[4]
        result.append(ue)

    return result


def usage_add(project_id, resource_id, samples, unit,
              start_at, end_at):
    session = get_session()

    try:
        # NOTE(flwang): For now, there is only one entry in the samples dict
        service, volume = samples.popitem()
        resource_ref = UsageEntry(service=service,
                                  volume=volume,
                                  unit=unit,
                                  resource_id=resource_id,
                                  tenant_id=project_id,
                                  start=start_at,
                                  end=end_at,
                                  created=datetime.utcnow())
        resource_ref.save(session=session)
    except sa.exc.InvalidRequestError as e:
        # FIXME(flwang): I assume there should be a DBDuplicateEntry error
        if str(e).rfind("Duplicate entry '\s' for key 'PRIMARY'"):
            LOG.warning(e)
            return
        raise e
    except Exception as e:
        raise e


def _get_resource(session, project_id, resource_id):
    return session.query(Resource).filter_by(
        id=resource_id, tenant_id=project_id).first()


def usages_add(project_id, resources, usage_entries, last_collect):
    """Add resources and usages for a project within one session.

    Update tenant.last_collected as well.
    """
    session = get_session()
    timestamp = datetime.utcnow()

    try:
        with session.begin(subtransactions=True):
            for (id, res_info) in six.iteritems(resources):
                res_db = _get_resource(session, project_id, id)
                if res_db:
                    orig_info = json.loads(res_db.info) or {}
                    orig_info.update(res_info)
                    res_db.info = json.dumps(orig_info)
                else:
                    resource_ref = Resource(
                        id=id,
                        info=json.dumps(res_info),
                        tenant_id=project_id,
                        created=timestamp
                    )
                    session.add(resource_ref)

            for entry in usage_entries:
                entry_db = UsageEntry(
                    service=entry['service'],
                    volume=entry['volume'],
                    unit=entry['unit'],
                    resource_id=entry['resource_id'],
                    tenant_id=entry['tenant_id'],
                    start=entry['start'],
                    end=entry['end'],
                    created=timestamp)
                session.add(entry_db)

            project_db = _project_get(session, project_id)
            project_db.last_collected = last_collect
    except Exception as e:
        session.rollback()
        raise exceptions.DBException(
            "Error occurs when adding usages, reason: %s" % str(e)
        )


def resource_add(project_id, resource_id, resource_info):
    session = get_session()
    resource_ref = Resource(
        id=resource_id, tenant_id=project_id, info=json.dumps(resource_info),
        created=datetime.utcnow()
    )

    try:
        resource_ref.save(session=session)
    except sa.exc.InvalidRequestError as e:
        # FIXME(flwang): I assume there should be a DBDuplicateEntry error
        if str(e).rfind("Duplicate entry '\s' for key 'PRIMARY'"):
            LOG.warning(e)
            return
        raise e
    except Exception as e:
        raise e


def resource_get_by_ids(project_id, resource_ids):
    session = get_session()
    query = session.query(Resource)

    query = (query.filter(Resource.id.in_(resource_ids)).
             filter(Resource.tenant_id == project_id))

    return query.all()


def get_project_locks(project_id):
    session = get_session()

    query = session.query(ProjectLock)
    query = query.filter(ProjectLock.project_id == project_id)

    try:
        return query.all()
    except Exception as e:
        raise exceptions.DBException(
            "Failed when querying database, error type: %s, "
            "error message: %s" % (e.__class__.__name__, str(e))
        )


@retry(stop_max_attempt_number=3, wait_fixed=5000)
def create_project_lock(project_id, owner):
    """Creates project lock record.

    This method has to work without SQLAlchemy session because session may not
    immediately issue an SQL query to a database and instead just schedule it
    whereas we need to make sure to issue a operation immediately.

    If there are more than 2 transactions trying to get same project lock
    (although with little chance), after the first one's commit, only one of
    the others will succeed to continue, all others will fail with exception.
    Using retry mechanism here to avoid that happen.
    """
    session = get_session()
    session.flush()

    insert = ProjectLock.__table__.insert()
    session.execute(insert.values(project_id=project_id, owner=owner,
                                  created=datetime.utcnow()))

    session.flush()


def ensure_project_lock(project_id, owner):
    """Make sure project lock record exists."""
    session = get_session()

    query = session.query(ProjectLock)
    query = query.filter(ProjectLock.project_id == project_id,
                         ProjectLock.owner == owner)

    # If there is already lock existing for the process, do not recreate. This
    # helps the process continue with the project it was handling before it was
    # killed.
    if not query.all():
        create_project_lock(project_id, owner)


def delete_project_lock(project_id):
    """Deletes project lock record.

    This method has to work without SQLAlchemy session because session may not
    immediately issue an SQL query to a database and instead just schedule it
    whereas we need to make sure to issue a operation immediately.
    """
    session = get_session()
    session.flush()

    table = ProjectLock.__table__
    delete = table.delete()
    session.execute(delete.where(table.c.project_id == project_id))

    session.flush()


@contextlib.contextmanager
def project_lock(project_id, owner):
    try:
        ensure_project_lock(project_id, owner)
        yield
    finally:
        delete_project_lock(project_id)
