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
import sys

from oslo_config import cfg
from oslo_db import exception as db_exception
from oslo_db.sqlalchemy import session as db_session
from oslo_log import log as logging
import sqlalchemy as sa

from distil import constants
from distil.db.sqlalchemy import models as m
from distil.db.sqlalchemy.models import Resource
from distil.db.sqlalchemy.models import Tenant
from distil.db.sqlalchemy.models import UsageEntry
from distil import exceptions

LOG = logging.getLogger(__name__)

CONF = cfg.CONF

_FACADE = None


def _create_facade_lazily():
    global _FACADE

    if _FACADE is None:
        params = dict(CONF.database.iteritems())
        params["sqlite_fk"] = True
        _FACADE = db_session.EngineFacade(
            CONF.database.connection,
            **params
        )
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


def _project_get(project_id):
    session = get_session()
    return session.query(Tenant).filter_by(id=project_id).first()


def project_add(values):
    project = _project_get(values.id)

    if not project:
        session = get_session()
        project = Tenant(id=values.id, name=values.name,
                         info=values.description, created=datetime.utcnow(),
                         last_collected=constants.dawn_of_time)

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


def usage_get(project_id, start_at, end_at):
    session = get_session()
    query = session.query(UsageEntry)

    query = (query.filter(UsageEntry.start_at >= start_at,
                          UsageEntry.end_at <= end_at).
             filter(UsageEntry.project_id == project_id))

    return query.all()


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


def usages_add(project_id, resources, usage_entries):
    """Add resources and usages for a project within one session.

    Update tenant.last_collected as well.
    """
    pass


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
