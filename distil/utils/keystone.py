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

from ceilometerclient import client as c_client
from keystoneclient.auth.identity import v3
from keystoneclient import session
from keystoneclient.v3 import client as ks_client
from oslo_config import cfg

CONF = cfg.CONF
KS_SESSION = None


def _get_keystone_session():
    global KS_SESSION

    if not KS_SESSION:
        auth = v3.Password(
            auth_url=CONF.keystone_authtoken.auth_url,
            username=CONF.keystone_authtoken.username,
            password=CONF.keystone_authtoken.password,
            project_name=CONF.keystone_authtoken.project_name,
            user_domain_name=CONF.keystone_authtoken.user_domain_name,
            project_domain_name=CONF.keystone_authtoken.project_domain_name,
        )
        KS_SESSION = session.Session(auth=auth, verify=False)

    return KS_SESSION


def get_keystone_client():
    sess = _get_keystone_session()
    return ks_client.Client(session=sess)


def get_ceilometer_client():
    sess = _get_keystone_session()

    return c_client.get_client(
        '2',
        session=sess,
        region_name=CONF.keystone_authtoken.region_name
    )


def get_projects():
    keystone = get_keystone_client()

    return [obj.to_dict() for obj in keystone.projects.list()]
