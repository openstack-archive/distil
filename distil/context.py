# Copyright (c) 2013 Mirantis Inc.
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

import eventlet
from eventlet.green import threading
from eventlet.green import time
from eventlet import greenpool
from eventlet import semaphore
from oslo_config import cfg

from distil.api import acl
from distil import exceptions as ex
from distil.i18n import _
from distil.i18n import _LE
from distil.i18n import _LW
from oslo_context import context
from oslo_log import log as logging


CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class Context(context.RequestContext):
    def __init__(self,
                 user_id=None,
                 tenant_id=None,
                 token=None,
                 service_catalog=None,
                 username=None,
                 tenant_name=None,
                 roles=None,
                 is_admin=None,
                 remote_semaphore=None,
                 auth_uri=None,
                 **kwargs):
        if kwargs:
            LOG.warn(_LW('Arguments dropped when creating context: %s'),
                     kwargs)
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.token = token
        self.service_catalog = service_catalog
        self.username = username
        self.tenant_name = tenant_name
        self.is_admin = is_admin
        self.remote_semaphore = remote_semaphore or semaphore.Semaphore(
            CONF.cluster_remote_threshold)
        self.roles = roles
        self.auth_uri = auth_uri

    def clone(self):
        return Context(
            self.user_id,
            self.tenant_id,
            self.token,
            self.service_catalog,
            self.username,
            self.tenant_name,
            self.roles,
            self.is_admin,
            self.remote_semaphore,
            self.auth_uri)

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'tenant_id': self.tenant_id,
            'token': self.token,
            'service_catalog': self.service_catalog,
            'username': self.username,
            'tenant_name': self.tenant_name,
            'is_admin': self.is_admin,
            'roles': self.roles,
            'auth_uri': self.auth_uri,
        }

    def is_auth_capable(self):
        return (self.service_catalog and self.token and self.tenant_id and
                self.user_id)


def get_admin_context():
    return Context(is_admin=True)


_CTX_STORE = threading.local()
_CTX_KEY = 'current_ctx'


def has_ctx():
    return hasattr(_CTX_STORE, _CTX_KEY)


def ctx():
    if not has_ctx():
        raise ex.IncorrectStateError(_("Context isn't available here"))
    return getattr(_CTX_STORE, _CTX_KEY)


def current():
    return ctx()


def set_ctx(new_ctx):
    if not new_ctx and has_ctx():
        delattr(_CTX_STORE, _CTX_KEY)

    if new_ctx:
        setattr(_CTX_STORE, _CTX_KEY, new_ctx)
