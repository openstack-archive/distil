# Copyright (C) 2014 Catalyst IT Ltd
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

import distil.transformers
from distil.constants import date_format, states
import unittest
import mock
import datetime

from distil.tests.unit import utils as unit_utils

p = lambda t: datetime.datetime.strptime(t, date_format)


class FAKE_DATA:
    t0 = p('2014-01-01T00:00:00')
    t0_10 = p('2014-01-01T00:10:00')
    t0_20 = p('2014-01-01T00:30:00')
    t0_30 = p('2014-01-01T00:30:00')
    t0_40 = p('2014-01-01T00:40:00')
    t0_50 = p('2014-01-01T00:50:00')
    t1 = p('2014-01-01T01:00:00')

    # and one outside the window
    tpre = p('2013-12-31T23:50:00')

    flavor = '1'
    flavor2 = '2'


class TestUptimeTransformer(unittest.TestCase):

    def _run_transform(self, data):
        xform = distil.transformers.Uptime()
        distil.config.setup_config(unit_utils.FAKE_CONFIG)
        with mock.patch('distil.helpers.flavor_name') as flavor_name:
            flavor_name.side_effect = lambda x: x
            return xform.transform_usage('state', data, FAKE_DATA.t0,
                                         FAKE_DATA.t1)

    def test_trivial_run(self):
        """
        Test that an no input data produces empty uptime.
        """
        state = []
        result = self._run_transform(state)
        self.assertEqual({}, result)

    def test_online_constant_flavor(self):
        """
        Test that a machine online for a 1h period with constant
        flavor works and gives 1h of uptime.
        """
        state = [
            {'timestamp': FAKE_DATA.t0, 'counter_volume': states['active'],
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor}},
            {'timestamp': FAKE_DATA.t1, 'counter_volume': states['active'],
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor}}
        ]

        result = self._run_transform(state)
        # there should be one hour of usage.
        self.assertEqual({FAKE_DATA.flavor: 3600}, result)

    def test_offline_constant_flavor(self):
        """
        Test that a machine offline for a 1h period with constant flavor
        works and gives zero uptime.
        """

        state = [
            {'timestamp': FAKE_DATA.t0, 'counter_volume': states['stopped'],
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor}},
            {'timestamp': FAKE_DATA.t1, 'counter_volume': states['stopped'],
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor}}
        ]

        result = self._run_transform(state)
        # there should be no usage, the machine was off.
        self.assertEqual({}, result)

    def test_shutdown_during_period(self):
        """
        Test that a machine run for 0.5 then shutdown gives 0.5h uptime.
        """
        state = [
            {'timestamp': FAKE_DATA.t0, 'counter_volume': states['active'],
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor}},
            {'timestamp': FAKE_DATA.t0_30, 'counter_volume': states['stopped'],
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor}},
            {'timestamp': FAKE_DATA.t1, 'counter_volume': states['stopped'],
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor}}
        ]

        result = self._run_transform(state)
        # there should be half an hour of usage.
        self.assertEqual({FAKE_DATA.flavor: 1800}, result)

    def test_online_flavor_change(self):
        """
        Test that a machine run for 0.5h as m1.tiny, resized to m1.large,
        and run for a further 0.5 yields 0.5h of uptime in each class.
        """
        state = [
            {'timestamp': FAKE_DATA.t0, 'counter_volume': states['active'],
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor}},
            {'timestamp': FAKE_DATA.t0_30, 'counter_volume': states['active'],
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor2}},
            {'timestamp': FAKE_DATA.t1, 'counter_volume': states['active'],
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor2}}
        ]

        result = self._run_transform(state)
        # there should be half an hour of usage in each of m1.tiny and m1.large
        self.assertEqual({FAKE_DATA.flavor: 1800, FAKE_DATA.flavor2: 1800},
                         result)

    def test_period_leadin_none_available(self):
        """
        Test that if the first data point is well into the window, and we had
        no lead-in data, we assume no usage until our first real data point.
        """
        state = [
            {'timestamp': FAKE_DATA.t0_10, 'counter_volume': states['active'],
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor}},
            {'timestamp': FAKE_DATA.t1, 'counter_volume': states['active'],
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor}}
        ]

        result = self._run_transform(state)
        # there should be 50 minutes of usage; we have no idea what happened
        # before that so we don't try to bill it.
        self.assertEqual({FAKE_DATA.flavor: 3000}, result)

    def test_period_leadin_available(self):
        """
        Test that if the first data point is well into the window, but we *do*
        have lead-in data, then we use the lead-in clipped to the start of the
        window.
        """
        state = [
            {'timestamp': FAKE_DATA.tpre, 'counter_volume': states['active'],
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor}},
            {'timestamp': FAKE_DATA.t0_10, 'counter_volume': states['active'],
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor}},
            {'timestamp': FAKE_DATA.t1, 'counter_volume': states['active'],
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor}}
        ]

        result = self._run_transform(state)
        # there should be 60 minutes of usage; we have no idea what
        # happened before that so we don't try to bill it.
        self.assertEqual({FAKE_DATA.flavor: 3600}, result)


class InstanceUptimeTransformerTests(unittest.TestCase):

    def _run_transform(self, data):
        xform = distil.transformers.InstanceUptime()
        distil.config.setup_config(unit_utils.FAKE_CONFIG)
        with mock.patch('distil.helpers.flavor_name') as flavor_name:
            flavor_name.side_effect = lambda x: x
            return xform.transform_usage('state', data, FAKE_DATA.t0,
                                         FAKE_DATA.t1)

    def test_trivial_run(self):
        """
        Test that an no input data produces empty uptime.
        """
        state = []
        result = self._run_transform(state)
        self.assertEqual({}, result)

    def test_online_constant_flavor(self):
        """
        Test that a machine online for a 1h period with constant
        flavor works and gives 1h of uptime.
        """
        state = [
            {'timestamp': FAKE_DATA.t0,
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor,
                                      'status': 'active'}},
            {'timestamp': FAKE_DATA.t1,
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor,
                                      'status': 'active'}}
        ]

        result = self._run_transform(state)
        # there should be one hour of usage.
        self.assertEqual({FAKE_DATA.flavor: 3600}, result)

    def test_offline_constant_flavor(self):
        """
        Test that a machine offline for a 1h period with constant flavor
        works and gives zero uptime.
        """

        state = [
            {'timestamp': FAKE_DATA.t0,
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor,
                                      'status': 'stopped'}},
            {'timestamp': FAKE_DATA.t1,
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor,
                                      'status': 'stopped'}}
        ]

        result = self._run_transform(state)
        # there should be no usage, the machine was off.
        self.assertEqual({}, result)

    def test_shutdown_during_period(self):
        """
        Test that a machine run for 0.5 then shutdown gives 0.5h uptime.
        """
        state = [
            {'timestamp': FAKE_DATA.t0,
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor,
                                      'status': 'active'}},
            {'timestamp': FAKE_DATA.t0_30,
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor,
                                      'status': 'stopped'}},
            {'timestamp': FAKE_DATA.t1,
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor,
                                      'status': 'stopped'}}
        ]

        result = self._run_transform(state)
        # there should be half an hour of usage.
        self.assertEqual({FAKE_DATA.flavor: 1800}, result)

    def test_online_flavor_change(self):
        """
        Test that a machine run for 0.5h as m1.tiny, resized to m1.large,
        and run for a further 0.5 yields 0.5h of uptime in each class.
        """
        state = [
            {'timestamp': FAKE_DATA.t0,
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor,
                                      'status': 'active'}},
            {'timestamp': FAKE_DATA.t0_30,
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor2,
                                      'status': 'active'}},
            {'timestamp': FAKE_DATA.t1,
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor2,
                                      'status': 'active'}}
        ]

        result = self._run_transform(state)
        # there should be half an hour of usage in each of m1.tiny and m1.large
        self.assertEqual({FAKE_DATA.flavor: 1800, FAKE_DATA.flavor2: 1800},
                         result)

    def test_period_leadin_none_available(self):
        """
        Test that if the first data point is well into the window, and we had
        no lead-in data, we assume no usage until our first real data point.
        """
        state = [
            {'timestamp': FAKE_DATA.t0_10,
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor,
                                      'status': 'active'}},
            {'timestamp': FAKE_DATA.t1,
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor,
                                      'status': 'active'}}
        ]

        result = self._run_transform(state)
        # there should be 50 minutes of usage; we have no idea what happened
        # before that so we don't try to bill it.
        self.assertEqual({FAKE_DATA.flavor: 3000}, result)

    def test_period_leadin_available(self):
        """
        Test that if the first data point is well into the window, but we *do*
        have lead-in data, then we use the lead-in clipped to the start of the
        window.
        """
        state = [
            {'timestamp': FAKE_DATA.tpre,
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor,
                                      'status': 'active'}},
            {'timestamp': FAKE_DATA.t0_10,
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor,
                                      'status': 'active'}},
            {'timestamp': FAKE_DATA.t1,
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor,
                                      'status': 'active'}}
        ]

        result = self._run_transform(state)
        # there should be 60 minutes of usage; we have no idea what
        # happened before that so we don't try to bill it.
        self.assertEqual({FAKE_DATA.flavor: 3600}, result)

    def test_notification_case(self):
        """
        Test that the transformer handles the notification metedata key,
        if/when it can't find the status key.
        """
        state = [
            {'timestamp': FAKE_DATA.t0,
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor,
                                      'state': 'active'}},
            {'timestamp': FAKE_DATA.t1,
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor,
                                      'state': 'active'}}
        ]

        result = self._run_transform(state)
        # there should be one hour of usage.
        self.assertEqual({FAKE_DATA.flavor: 3600}, result)

    def test_no_state_in_metedata(self):
        """
        Test that the transformer doesn't fall over if there isn't one of
        the two state/status key options in the metadata.
        """
        state = [
            {'timestamp': FAKE_DATA.t0,
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor}},
            {'timestamp': FAKE_DATA.t1,
                'resource_metadata': {'flavor.id': FAKE_DATA.flavor}}
        ]

        result = self._run_transform(state)
        # there should no usage.
        self.assertEqual({}, result)


class GaugeMaxTransformerTests(unittest.TestCase):

    def test_all_different_values(self):
        """
        Tests that the transformer correctly grabs the highest value,
        when all values are different.
        """

        data = [
            {'timestamp': FAKE_DATA.t0, 'counter_volume': 12},
            {'timestamp': FAKE_DATA.t0_10, 'counter_volume': 3},
            {'timestamp': FAKE_DATA.t0_20, 'counter_volume': 7},
            {'timestamp': FAKE_DATA.t0_30, 'counter_volume': 3},
            {'timestamp': FAKE_DATA.t0_40, 'counter_volume': 25},
            {'timestamp': FAKE_DATA.t0_50, 'counter_volume': 2},
            {'timestamp': FAKE_DATA.t1, 'counter_volume': 6},
        ]

        xform = distil.transformers.GaugeMax()
        usage = xform.transform_usage('some_meter', data, FAKE_DATA.t0,
                                      FAKE_DATA.t1)

        self.assertEqual({'some_meter': 25}, usage)

    def test_all_same_values(self):
        """
        Tests that that transformer correctly grabs any value,
        when all values are the same.
        """

        data = [
            {'timestamp': FAKE_DATA.t0, 'counter_volume': 25},
            {'timestamp': FAKE_DATA.t0_30, 'counter_volume': 25},
            {'timestamp': FAKE_DATA.t1, 'counter_volume': 25},
        ]

        xform = distil.transformers.GaugeMax()
        usage = xform.transform_usage('some_meter', data, FAKE_DATA.t0,
                                      FAKE_DATA.t1)

        self.assertEqual({'some_meter': 25}, usage)

    def test_none_value(self):
        """
        Tests that that transformer correctly handles a None value.
        """

        data = [
            {'timestamp': FAKE_DATA.t0, 'counter_volume': None},
        ]

        xform = distil.transformers.GaugeMax()
        usage = xform.transform_usage('some_meter', data, FAKE_DATA.t0,
                                      FAKE_DATA.t1)

        self.assertEqual({'some_meter': 0}, usage)

    def test_none_and_other_values(self):
        """
        Tests that that transformer correctly handles a None value.
        """

        data = [
            {'timestamp': FAKE_DATA.t0, 'counter_volume': None},
            {'timestamp': FAKE_DATA.t0_30, 'counter_volume': 25},
            {'timestamp': FAKE_DATA.t1, 'counter_volume': 27},
        ]

        xform = distil.transformers.GaugeMax()
        usage = xform.transform_usage('some_meter', data, FAKE_DATA.t0,
                                      FAKE_DATA.t1)

        self.assertEqual({'some_meter': 27}, usage)


class StorageMaxTransformerTests(unittest.TestCase):

    def test_all_different_values(self):
        """
        Tests that the transformer correctly grabs the highest value,
        when all values are different.
        """

        data = [
            {'timestamp': FAKE_DATA.t0, 'counter_volume': 12,
             'resource_metadata': {}},
            {'timestamp': FAKE_DATA.t0_10, 'counter_volume': 3,
             'resource_metadata': {}},
            {'timestamp': FAKE_DATA.t0_20, 'counter_volume': 7,
             'resource_metadata': {}},
            {'timestamp': FAKE_DATA.t0_30, 'counter_volume': 3,
             'resource_metadata': {}},
            {'timestamp': FAKE_DATA.t0_40, 'counter_volume': 25,
             'resource_metadata': {}},
            {'timestamp': FAKE_DATA.t0_50, 'counter_volume': 2,
             'resource_metadata': {}},
            {'timestamp': FAKE_DATA.t1, 'counter_volume': 6,
             'resource_metadata': {}},
        ]

        xform = distil.transformers.StorageMax()
        usage = xform.transform_usage('some_meter', data, FAKE_DATA.t0,
                                      FAKE_DATA.t1)

        self.assertEqual({'some_meter': 25}, usage)

    def test_all_same_values(self):
        """
        Tests that that transformer correctly grabs any value,
        when all values are the same.
        """

        data = [
            {'timestamp': FAKE_DATA.t0, 'counter_volume': 25,
             'resource_metadata': {}},
            {'timestamp': FAKE_DATA.t0_30, 'counter_volume': 25,
             'resource_metadata': {}},
            {'timestamp': FAKE_DATA.t1, 'counter_volume': 25,
             'resource_metadata': {}},
        ]

        xform = distil.transformers.StorageMax()
        usage = xform.transform_usage('some_meter', data, FAKE_DATA.t0,
                                      FAKE_DATA.t1)

        self.assertEqual({'some_meter': 25}, usage)

    def test_none_value(self):
        """
        Tests that that transformer correctly handles a None value.
        """

        data = [
            {'timestamp': FAKE_DATA.t0, 'counter_volume': None,
             'resource_metadata': {}},
        ]

        xform = distil.transformers.StorageMax()
        usage = xform.transform_usage('some_meter', data, FAKE_DATA.t0,
                                      FAKE_DATA.t1)

        self.assertEqual({'some_meter': 0}, usage)

    def test_none_and_other_values(self):
        """
        Tests that that transformer correctly handles a None value.
        """

        data = [
            {'timestamp': FAKE_DATA.t0, 'counter_volume': None,
             'resource_metadata': {}},
            {'timestamp': FAKE_DATA.t0_30, 'counter_volume': 25,
             'resource_metadata': {}},
            {'timestamp': FAKE_DATA.t1, 'counter_volume': 27,
             'resource_metadata': {}},
        ]

        xform = distil.transformers.StorageMax()
        usage = xform.transform_usage('some_meter', data, FAKE_DATA.t0,
                                      FAKE_DATA.t1)

        self.assertEqual({'some_meter': 27}, usage)


class TestGaugeSumTransformer(unittest.TestCase):

    def test_basic_sum(self):
        """
        Tests that the transformer correctly calculate the sum value.
        """

        data = [
            {'timestamp': p('2014-01-01T00:00:00'), 'counter_volume': 1},
            {'timestamp': p('2014-01-01T00:10:00'), 'counter_volume': 1},
            {'timestamp': p('2014-01-01T01:00:00'), 'counter_volume': 1},
        ]

        xform = distil.transformers.GaugeSum()
        usage = xform.transform_usage('fake_meter', data, FAKE_DATA.t0,
                                      FAKE_DATA.t1)

        self.assertEqual({'fake_meter': 2}, usage)

    def test_none_value(self):
        """
        Tests that that transformer correctly handles a None value.
        """

        data = [
            {'timestamp': FAKE_DATA.t0, 'counter_volume': None},
        ]

        xform = distil.transformers.GaugeSum()
        usage = xform.transform_usage('some_meter', data, FAKE_DATA.t0,
                                      FAKE_DATA.t1)

        self.assertEqual({'some_meter': 0}, usage)

    def test_none_and_other_values(self):
        """
        Tests that that transformer correctly handles a None value.
        """

        data = [
            {'timestamp': FAKE_DATA.t0, 'counter_volume': None},
            {'timestamp': FAKE_DATA.t0_30, 'counter_volume': 25},
            {'timestamp': FAKE_DATA.t0_50, 'counter_volume': 25},
        ]

        xform = distil.transformers.GaugeSum()
        usage = xform.transform_usage('some_meter', data, FAKE_DATA.t0,
                                      FAKE_DATA.t1)

        self.assertEqual({'some_meter': 50}, usage)


class TestFromImageTransformer(unittest.TestCase):
    """
    These tests rely on config settings for from_image,
    as defined in test constants, or in conf.yaml
    """

    def test_from_volume_case(self):
        """
        If instance is booted from volume transformer should return none.
        """
        data = [
            {'timestamp': FAKE_DATA.t0,
                'resource_metadata': {'image_ref': ""}},
            {'timestamp': FAKE_DATA.t0_30,
                'resource_metadata': {'image_ref': "None"}},
            {'timestamp': FAKE_DATA.t1,
                'resource_metadata': {'image_ref': "None"}}
        ]

        data2 = [
            {'timestamp': FAKE_DATA.t0_30,
                'resource_metadata': {'image_ref': "None"}}
        ]

        xform = distil.transformers.FromImage()
        distil.config.setup_config(unit_utils.FAKE_CONFIG)
        usage = xform.transform_usage('instance', data, FAKE_DATA.t0,
                                      FAKE_DATA.t1)
        usage2 = xform.transform_usage('instance', data2, FAKE_DATA.t0,
                                       FAKE_DATA.t1)

        self.assertEqual(None, usage)
        self.assertEqual(None, usage2)

    def test_default_to_from_volume_case(self):
        """
        Unless all image refs contain something, assume booted from volume.
        """
        data = [
            {'timestamp': FAKE_DATA.t0,
                'resource_metadata': {'image_ref': ""}},
            {'timestamp': FAKE_DATA.t0_30,
                'resource_metadata': {'image_ref': "d5a4f118023928195f4ef"}},
            {'timestamp': FAKE_DATA.t1,
                'resource_metadata': {'image_ref': "None"}}
        ]

        xform = distil.transformers.FromImage()
        distil.config.setup_config(unit_utils.FAKE_CONFIG)
        usage = xform.transform_usage('instance', data, FAKE_DATA.t0,
                                      FAKE_DATA.t1)

        self.assertEqual(None, usage)

    def test_from_image_case(self):
        """
        If all image refs contain something, should return entry.
        """
        data = [
            {'timestamp': FAKE_DATA.t0,
                'resource_metadata': {'image_ref': "d5a4f118023928195f4ef",
                                      'root_gb': "20"}},
            {'timestamp': FAKE_DATA.t0_30,
                'resource_metadata': {'image_ref': "d5a4f118023928195f4ef",
                                      'root_gb': "20"}},
            {'timestamp': FAKE_DATA.t1,
                'resource_metadata': {'image_ref': "d5a4f118023928195f4ef",
                                      'root_gb': "20"}}
        ]

        xform = distil.transformers.FromImage()
        distil.config.setup_config(unit_utils.FAKE_CONFIG)
        usage = xform.transform_usage('instance', data, FAKE_DATA.t0,
                                      FAKE_DATA.t1)

        self.assertEqual({'volume.size': 20}, usage)

    def test_from_image_case_highest_size(self):
        """
        If all image refs contain something,
        should return entry with highest size from data.
        """
        data = [
            {'timestamp': FAKE_DATA.t0,
                'resource_metadata': {'image_ref': "d5a4f118023928195f4ef",
                                      'root_gb': "20"}},
            {'timestamp': FAKE_DATA.t0_30,
                'resource_metadata': {'image_ref': "d5a4f118023928195f4ef",
                                      'root_gb': "60"}},
            {'timestamp': FAKE_DATA.t1,
                'resource_metadata': {'image_ref': "d5a4f118023928195f4ef",
                                      'root_gb': "20"}}
        ]

        xform = distil.transformers.FromImage()
        distil.config.setup_config(unit_utils.FAKE_CONFIG)
        usage = xform.transform_usage('instance', data, FAKE_DATA.t0,
                                      FAKE_DATA.t1)

        self.assertEqual({'volume.size': 60}, usage)


class TestGaugeNetworkServiceTransformer(unittest.TestCase):

        def test_basic_sum(self):
            """Tests that the transformer correctly calculate the sum value.
            """

            data = [
                {'timestamp': p('2014-01-01T00:00:00'), 'counter_volume': 1},
                {'timestamp': p('2014-01-01T00:10:00'), 'counter_volume': 0},
                {'timestamp': p('2014-01-01T01:00:00'), 'counter_volume': 2},
            ]

            xform = distil.transformers.GaugeNetworkService()
            usage = xform.transform_usage('fake_meter', data, FAKE_DATA.t0,
                                          FAKE_DATA.t1)

            self.assertEqual({'fake_meter': 1}, usage)

        def test_only_pending_service(self):
            """Tests that the transformer correctly calculate the sum value.
            """

            data = [
                {'timestamp': p('2014-01-01T00:00:00'), 'counter_volume': 2},
                {'timestamp': p('2014-01-01T00:10:00'), 'counter_volume': 2},
                {'timestamp': p('2014-01-01T01:00:00'), 'counter_volume': 2},
            ]

            xform = distil.transformers.GaugeNetworkService()
            usage = xform.transform_usage('fake_meter', data, FAKE_DATA.t0,
                                          FAKE_DATA.t1)

            self.assertEqual({'fake_meter': 0}, usage)
