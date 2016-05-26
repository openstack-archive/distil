# Copyright 2016 Catalyst IT Ltd
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

from keystoneclient.auth.identity import v3
from keystoneclient import session
from keystoneclient.v3 import client as ks_client
from oslo_config import cfg

CONF = cfg.CONF
KS_CLIENT = None


def get_keystone_client():
    global KS_CLIENT

    if not KS_CLIENT:
        auth = v3.Password(
            auth_url=CONF.keystone_authtoken.auth_url,
            username=CONF.keystone_authtoken.admin_user,
            password=CONF.keystone_authtoken.admin_password,
            project_name=CONF.keystone_authtoken.admin_tenant_name,
            user_domain_name='default',
            project_domain_name='default'
        )
        sess = session.Session(auth=auth, verify=False)
        KS_CLIENT = ks_client.Client(session=sess)

    return KS_CLIENT


def get_projects():
    keystone = get_keystone_client()

    return [obj.to_dict() for obj in keystone.projects.list()]
