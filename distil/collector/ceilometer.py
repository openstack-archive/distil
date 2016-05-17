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

from distil.collector import base

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class CeilometerCollector(base.BaseCollector):
    def __init__(self, *arg, **kwargs):
        super(CeilometerCollector, self).__init__(*arg, **kwargs)

    def _get_client(self):
        pass

    def get_meter(self, project_id, meter, start, end):
        return [
            {
                "id": "9b23b398-6139-11e5-97e9-bc764e045bf6",
                "resource_metadata": {
                    "availability_zone": "zone1",
                    "display_name": "volume_name"
                },
                "meter": "volume.size",
                "project_id": "35b17138-b364-4e6a-a131-8f3099c5be68",
                "recorded_at": "2015-09-22T14:52:54.850725",
                "resource_id": "bd9431c1-8d69-4ad3-803a-8d4a6b89fd36",
                "source": "openstack",
                "timestamp": "2015-09-22T14:52:54.850718",
                "type": "gauge",
                "unit": "GB",
                "user_id": "efd87807-12d2-4b38-9c70-5f5c2ac427ff",
                "counter_volume": 1
            }
        ]
