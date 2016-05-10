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

from datetime import datetime
import json
import six
import sys

import sqlalchemy as sa
from sqlalchemy import func
import threading

from oslo_config import cfg
from oslo_db import exception as db_exception
from oslo_db.sqlalchemy import session as db_session
from oslo_log import log as logging

from distil.db.sqlalchemy import models as m
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
        m.Cluster.metadata.create_all(engine)
    except sa.exc.OperationalError as e:
        LOG.exception("Database registration exception: %s", e)
        return False
    return True


def drop_db():
    try:
        engine = get_engine()
        m.Cluster.metadata.drop_all(engine)
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


def _project_get(session, project_id):
    return session.query(Tenant).filter_by(id=project_id).first()


def project_add(values):
    session = get_session()
    project = _project_get(session, values['id'])

    if not project:
        # In fact, it should be the project created time.
        start_time = datetime.strptime(
            CONF.collector.dawn_of_time,
            "%Y-%m-%d %H:%M:%S"
        )

        project = Tenant(id=values['id'], name=values['name'],
                         info=values['description'], created=datetime.utcnow(),
                         last_collected=start_time)

        try:
            project.save(session=session)
        except db_exception.DBDuplicateEntry as e:
            raise exceptions.DuplicateException(
                "Duplicate entry for Tenant: %s" % e.columns
            )

    return project


def project_get_all():
    session = get_session()
    query = session.query(Tenant)
    return query.all()


def project_get(project_id):
    session = get_session()
    query = session.query(Tenant)
    query = query.filter(Tenant.id == project_id)
    try:
        return query.one()
    except Exception:
        raise exceptions.NotFoundException(project_id)


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
                                  project_id=project_id,
                                  start_at=start_at, end_at=end_at)
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
            for (id, res) in six.iteritems(resources):
                res_db = _get_resource(session, project_id, id)
                if res_db:
                    res_db.info = json.dumps(res['info'])
                else:
                    resource_ref = Resource(
                        id=id,
                        info=json.dumps(res['info']),
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


def resource_add(project_id, resource_id, resource_type, raw, metadata):
    session = get_session()
    metadata = _merge_resource_metadata({'type': resource_type}, raw, metadata)
    resource_ref = Resource(id=resource_id, project_id=project_id,
                            resource_type=resource_type, meta_data=metadata)

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


def _merge_resource_metadata(md_dict, entry, md_def):
    """Strips metadata from the entry as defined in the config,
       and merges it with the given metadata dict.
    """
    for field, parameters in md_def.iteritems():
        for _, source in enumerate(parameters['sources']):
            try:
                value = entry['resource_metadata'][source]
                if 'template' in parameters:
                    md_dict[field] = parameters['template'] % value
                    break
                else:
                    md_dict[field] = value
                    break
            except KeyError:
                # Just means we haven't found the right value yet.
                # Or value isn't present.
                pass

    return md_dict
