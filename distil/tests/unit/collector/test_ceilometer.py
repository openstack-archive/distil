# Copyright (C) 2017 Catalyst IT Ltd
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
import os
from datetime import datetime
from datetime import timedelta

import mock

from distil.collector import ceilometer
from distil.tests.unit import base

FAKE_PROJECT = '123'
FAKE_METER = 'instance'
START = END = datetime.utcnow()


class CeilometerCollectorTest(base.DistilTestCase):
    def setUp(self):
        super(CeilometerCollectorTest, self).setUp()

        meter_mapping_file = os.path.join(
            os.environ["DISTIL_TESTS_CONFIGS_DIR"],
            'meter_mappings.yaml'
        )
        self.conf.set_default(
            'meter_mappings_file',
            meter_mapping_file,
            group='collector'
        )

    @mock.patch('distil.common.openstack.get_ceilometer_client')
    def test_get_meter(self, mock_cclient):
        class Sample(object):
            def __init__(self, id, timestamp):
                self.id = id
                self.timestamp = timestamp

            def to_dict(self):
                return {'meter': 'instance', 'resource_id': self.id,
                        'timestamp': self.timestamp}

        s1 = Sample('111', (datetime.utcnow() + timedelta(days=3)))
        s2 = Sample('222', (datetime.utcnow() + timedelta(days=2)))
        s3 = Sample('333', (datetime.utcnow() + timedelta(days=1)))

        cclient = mock.Mock()
        mock_cclient.return_value = cclient
        cclient.new_samples.list.return_value = [s1, s2, s3]

        collector = ceilometer.CeilometerCollector()
        samples = collector.get_meter(FAKE_PROJECT, FAKE_METER, START, END)

        expected = [s3.to_dict(), s2.to_dict(), s1.to_dict()]

        self.assertEqual(expected, samples)
