# Copyright (c) 2013 Mirantis Inc.
# Copyright 2014 Catalyst IT Ltd

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

"""Defines interface for DB access.

Functions in this module are imported into the distil.db namespace. Call these
functions from distil.db namespace, not the distil.db.api namespace.

All functions in this module return objects that implement a dictionary-like
interface.

**Related Flags**

:db_backend:  string to lookup in the list of LazyPluggable backends.
              `sqlalchemy` is the only supported backend right now.

:sql_connection:  string specifying the sqlalchemy connection to use, like:
                  `sqlite:///var/lib/distil/distil.sqlite`.

"""
import contextlib

from oslo_config import cfg
from oslo_db import api as db_api
from oslo_db import options
from oslo_log import log as logging

CONF = cfg.CONF

options.set_defaults(CONF)

_BACKEND_MAPPING = {
    'sqlalchemy': 'distil.db.sqlalchemy.api',
}

IMPL = db_api.DBAPI.from_config(CONF, backend_mapping=_BACKEND_MAPPING)
LOG = logging.getLogger(__name__)


def setup_db():
    """Set up database, create tables, etc.

    Return True on success, False otherwise
    """
    return IMPL.setup_db()


def drop_db():
    """Drop database.

    Return True on success, False otherwise
    """
    return IMPL.drop_db()


def to_dict(func):
    def decorator(*args, **kwargs):
        res = func(*args, **kwargs)

        if isinstance(res, list):
            return [item.to_dict() for item in res]

        if res:
            return res.to_dict()
        else:
            return None

    return decorator


def usage_get(project_id, start_at, end_at):
    """Get usage for specific tenant based on time range.

    """
    return IMPL.usage_get(project_id, start_at, end_at)


def usage_add(project_id, resource_id, samples, unit,
              start_at, end_at):
    """If a tenant exists does nothing,
       and if it doesn't, creates and inserts it.
    """
    return IMPL.usage_add(project_id, resource_id, samples, unit,
                          start_at, end_at)


def usages_add(project_id, resources, usage_entries, last_collect):
    return IMPL.usages_add(project_id, resources, usage_entries, last_collect)


def resource_add(project_id, resource_id, resource_info):
    return IMPL.resource_add(project_id, resource_id, resource_info)


def project_add(values, last_collect=None):
    return IMPL.project_add(values, last_collect)


def resource_get_by_ids(project_id, resource_ids):
    return IMPL.resource_get_by_ids(project_id, resource_ids)


def project_get(project_id):
    return IMPL.project_get(project_id)


def project_get_all():
    return IMPL.project_get_all()


def get_last_collect(project_ids):
    return IMPL.get_last_collect(project_ids)


# Project Locks.

def create_project_lock(project_id, owner):
    return IMPL.create_project_lock(project_id, owner)


def get_project_locks(project_id):
    return IMPL.get_project_locks(project_id)


def ensure_project_lock(project_id, owner):
    return IMPL.ensure_project_lock(project_id, owner)


def delete_project_lock(project_id):
    return IMPL.delete_project_lock(project_id)


@contextlib.contextmanager
def project_lock(project_id, owner):
    with IMPL.project_lock(project_id, owner):
        yield
