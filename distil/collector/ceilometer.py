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

from oslo_config import cfg
from oslo_log import log as logging
from ceilometerclient import client
from keystoneclient.auth.identity import v3
from keystoneclient import session

from distil.collector import base
from distil import constants

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class CeilometerCollector(base.BaseCollector):
    def __init__(self, *arg, **kwargs):
        super(CeilometerCollector, self).__init__(*arg, **kwargs)

        auth = v3.Password(
            auth_url=CONF.keystone_authtoken.auth_url,
            username=CONF.keystone_authtoken.username,
            password=CONF.keystone_authtoken.password,
            project_name=CONF.keystone_authtoken.project_name,
            user_domain_name=CONF.keystone_authtoken.user_domain_name,
            project_domain_name=CONF.keystone_authtoken.project_domain_name
        )
        sess = session.Session(auth=auth, verify=False)

        self.cclient = client.get_client(
            '2',
            session=sess,
            region_name=CONF.keystone_authtoken.region_name
        )

    def get_meter(self, project_id, meter, start, end):
        """Get samples of a particular meter.

        Sample example:
        [
            {
                "id": "e04ace6e-2229-11e6-ad16-bc764e068568",
                "metadata": {
                    "name1": "value1",
                    "name2": "value2"
                },
                "meter": "instance",
                "project_id": "35b17138-b364-4e6a-a131-8f3099c5be68",
                "recorded_at": "2015-01-01T12:00:00",
                "resource_id": "bd9431c1-8d69-4ad3-803a-8d4a6b89fd36",
                "source": "openstack",
                "timestamp": "2015-01-01T12:00:00",
                "type": "gauge",
                "unit": "instance",
                "user_id": "efd87807-12d2-4b38-9c70-5f5c2ac427ff",
                "volume": 1.0
            }
        ]
        """
        query = [
            dict(field='project_id', op='eq', value=project_id),
            dict(field='meter', op='eq', value=meter),
            dict(field='timestamp', op='ge',
                 value=start.strftime(constants.date_format)),
            dict(field='timestamp', op='lt',
                 value=end.strftime(constants.date_format)),
        ]

        sample_objs = self.cclient.new_samples.list(q=query)

        return [obj.to_dict() for obj in sample_objs]
