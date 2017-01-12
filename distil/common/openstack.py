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

from ceilometerclient import client as ceilometerclient
from cinderclient.v2 import client as cinderclient
from glanceclient import client as glanceclient
from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneclient.v3 import client as ks_client
from novaclient import client as novaclient
from oslo_config import cfg

from distil.common import general

CONF = cfg.CONF
KS_SESSION = None
cache = {}


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

    return ceilometerclient.get_client(
        '2',
        session=sess,
        region_name=CONF.keystone_authtoken.region_name
    )


def get_cinder_client():
    sess = _get_keystone_session()

    return cinderclient.Client(
        session=sess,
        region_name=CONF.keystone_authtoken.region_name
    )


def get_glance_client():
    sess = _get_keystone_session()

    return glanceclient.Client(
        '2',
        session=sess,
        region_name=CONF.keystone_authtoken.region_name
    )


def get_nova_client():
    sess = _get_keystone_session()

    return novaclient.Client(
        '2',
        session=sess,
        region_name=CONF.keystone_authtoken.region_name
    )


@general.disable_ssl_warnings
def get_projects():
    keystone = get_keystone_client()

    return [obj.to_dict() for obj in keystone.projects.list()]


@general.disable_ssl_warnings
def get_regions():
    keystone = get_keystone_client()

    return keystone.regions.list()


@general.disable_ssl_warnings
def get_image(image_id):
    glance = get_glance_client()
    return glance.images.get(image_id)


@general.disable_ssl_warnings
def get_volume(instance_id):
    nova = get_nova_client()
    instance = nova.servers.get(instance_id)

    # Assume first volume is the root disk
    volume_id = getattr(
        instance, 'os-extended-volumes:volumes_attached')[0]['id']
    if not volume_id:
        return None

    cinder = get_cinder_client()
    return cinder.volumes.get(volume_id)


@general.disable_ssl_warnings
def get_volume_type(volume_type):
    if not cache['volume_types']:
        cinder = get_cinder_client()
        for vtype in cinder.volume_types.list():
            cache['volume_types'].append({'id': vtype.id, 'name': vtype.name})

    for vtype in cache['volume_types']:
        # check name first, as that will be more common
        if vtype['name'] == volume_type:
            return volume_type
        elif vtype['id'] == volume_type:
            return vtype['name']

    return None


@general.disable_ssl_warnings
def get_flavor_name(flavor_id):
    """Grabs the correct flavor name from Nova given the correct ID."""
    if flavor_id not in cache:
        nova = get_nova_client()
        cache[flavor_id] = nova.flavors.get(flavor_id).name
    return cache[flavor_id]
