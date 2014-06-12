import distil.transformers
from distil import constants
from distil.constants import states
import unittest
import mock
import datetime


class testdata:
    # string timestamps to put in meter data
    t0 = '2014-01-01T00:00:00'
    t0_10 = '2014-01-01T00:10:00'
    t0_20 = '2014-01-01T00:30:00'
    t0_30 = '2014-01-01T00:30:00'
    t0_40 = '2014-01-01T00:40:00'
    t0_50 = '2014-01-01T00:50:00'
    t1 = '2014-01-01T01:00:00'

    # and one outside the window
    tpre = '2013-12-31T23:50:00'

    # clipping window bounds -- expected to be actual datetimes.
    ts0 = datetime.datetime.strptime(t0, constants.date_format)
    ts1 = datetime.datetime.strptime(t1, constants.date_format)

    flavor = '1'
    flavor2 = '2'


class TestMeter(object):
    def __init__(self, data, mtype=None):
        self.data = data
        self.type = mtype

    def usage(self):
        return self.data


class UptimeTransformerTests(unittest.TestCase):

    def _run_transform(self, data):
        xform = distil.transformers.Uptime()
        with mock.patch('distil.helpers.flavor_name') as flavor_name:
            flavor_name.side_effect = lambda x: x
            return xform.transform_usage('state', data, testdata.ts0,
                                         testdata.ts1)

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
            {'timestamp': testdata.t0, 'counter_volume': states['active'],
                'resource_metadata': {'flavor.id': testdata.flavor}},
            {'timestamp': testdata.t1, 'counter_volume': states['active'],
                'resource_metadata': {'flavor.id': testdata.flavor}}
        ]

        result = self._run_transform(state)
        # there should be one hour of usage.
        self.assertEqual({testdata.flavor: 3600}, result)

    def test_offline_constant_flavor(self):
        """
        Test that a machine offline for a 1h period with constant flavor
        works and gives zero uptime.
        """

        state = [
            {'timestamp': testdata.t0, 'counter_volume': states['stopped'],
                'resource_metadata': {'flavor.id': testdata.flavor}},
            {'timestamp': testdata.t1, 'counter_volume': states['stopped'],
                'resource_metadata': {'flavor.id': testdata.flavor}}
        ]

        result = self._run_transform(state)
        # there should be no usage, the machine was off.
        self.assertEqual({}, result)

    def test_shutdown_during_period(self):
        """
        Test that a machine run for 0.5 then shutdown gives 0.5h uptime.
        """
        state = [
            {'timestamp': testdata.t0, 'counter_volume': states['active'],
                'resource_metadata': {'flavor.id': testdata.flavor}},
            {'timestamp': testdata.t0_30, 'counter_volume': states['stopped'],
                'resource_metadata': {'flavor.id': testdata.flavor}},
            {'timestamp': testdata.t1, 'counter_volume': states['stopped'],
                'resource_metadata': {'flavor.id': testdata.flavor}}
        ]

        result = self._run_transform(state)
        # there should be half an hour of usage.
        self.assertEqual({testdata.flavor: 1800}, result)

    def test_online_flavor_change(self):
        """
        Test that a machine run for 0.5h as m1.tiny, resized to m1.large,
        and run for a further 0.5 yields 0.5h of uptime in each class.
        """
        state = [
            {'timestamp': testdata.t0, 'counter_volume': states['active'],
                'resource_metadata': {'flavor.id': testdata.flavor}},
            {'timestamp': testdata.t0_30, 'counter_volume': states['active'],
                'resource_metadata': {'flavor.id': testdata.flavor2}},
            {'timestamp': testdata.t1, 'counter_volume': states['active'],
                'resource_metadata': {'flavor.id': testdata.flavor2}}
        ]

        result = self._run_transform(state)
        # there should be half an hour of usage in each of m1.tiny and m1.large
        self.assertEqual({testdata.flavor: 1800, testdata.flavor2: 1800},
                         result)

    def test_period_leadin_none_available(self):
        """
        Test that if the first data point is well into the window, and we had
        no lead-in data, we assume no usage until our first real data point.
        """
        state = [
            {'timestamp': testdata.t0_10, 'counter_volume': states['active'],
                'resource_metadata': {'flavor.id': testdata.flavor}},
            {'timestamp': testdata.t1, 'counter_volume': states['active'],
                'resource_metadata': {'flavor.id': testdata.flavor}}
        ]

        result = self._run_transform(state)
        # there should be 50 minutes of usage; we have no idea what happened
        # before that so we don't try to bill it.
        self.assertEqual({testdata.flavor: 3000}, result)

    def test_period_leadin_available(self):
        """
        Test that if the first data point is well into the window, but we *do*
        have lead-in data, then we use the lead-in clipped to the start of the
        window.
        """
        state = [
            {'timestamp': testdata.tpre, 'counter_volume': states['active'],
                'resource_metadata': {'flavor.id': testdata.flavor}},
            {'timestamp': testdata.t0_10, 'counter_volume': states['active'],
                'resource_metadata': {'flavor.id': testdata.flavor}},
            {'timestamp': testdata.t1, 'counter_volume': states['active'],
                'resource_metadata': {'flavor.id': testdata.flavor}}
        ]

        result = self._run_transform(state)
        # there should be 60 minutes of usage; we have no idea what
        # happened before that so we don't try to bill it.
        self.assertEqual({testdata.flavor: 3600}, result)


class GaugeMaxTransformerTests(unittest.TestCase):

    def test_all_different_values(self):
        """
        Tests that the transformer correctly grabs the highest value,
        when all values are different.
        """

        data = [
            {'timestamp': testdata.t0, 'counter_volume': 12},
            {'timestamp': testdata.t0_10, 'counter_volume': 3},
            {'timestamp': testdata.t0_20, 'counter_volume': 7},
            {'timestamp': testdata.t0_30, 'counter_volume': 3},
            {'timestamp': testdata.t0_40, 'counter_volume': 25},
            {'timestamp': testdata.t0_50, 'counter_volume': 2},
            {'timestamp': testdata.t1, 'counter_volume': 6},
        ]

        xform = distil.transformers.GaugeMax()
        usage = xform.transform_usage('some_meter', data, testdata.ts0,
                                      testdata.ts1)

        self.assertEqual({'some_meter': 25}, usage)

    def test_all_same_values(self):
        """
        Tests that that transformer correctly grabs any value,
        when all values are the same.
        """

        data = [
            {'timestamp': testdata.t0, 'counter_volume': 25},
            {'timestamp': testdata.t0_30, 'counter_volume': 25},
            {'timestamp': testdata.t1, 'counter_volume': 25},
        ]

        xform = distil.transformers.GaugeMax()
        usage = xform.transform_usage('some_meter', data, testdata.ts0,
                                      testdata.ts1)

        self.assertEqual({'some_meter': 25}, usage)
