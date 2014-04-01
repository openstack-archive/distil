import artifice.transformers
from artifice.transformers import TransformerValidationError
from artifice import constants
from artifice.constants import states
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

    flavor = 'm1.tiny'
    flavor2 = 'm1.large'


class TestMeter(object):
    def __init__(self, data, mtype=None):
        self.data = data
        self.type = mtype

    def usage(self):
        return self.data


class UptimeTransformerTests(unittest.TestCase):
    def test_required_metrics_not_present(self):
        """
        Test that the correct exception is thrown if one of the required meters
        is not present.
        """
        xform = artifice.transformers.Uptime()

        with self.assertRaises(TransformerValidationError) as e:
            xform.transform_usage({}, testdata.ts0, testdata.ts1)

        self.assertTrue(e.exception.message.startswith('Required meters:'))

    def _run_transform(self, meters):
        xform = artifice.transformers.Uptime()
        with mock.patch('artifice.helpers.flavor_name') as flavor_name:
            flavor_name.side_effect = lambda x: x
            return xform.transform_usage(meters, testdata.ts0, testdata.ts1)

    def test_trivial_run(self):
        """
        Test that an no input data produces empty uptime.
        """
        meters = {
            'flavor': TestMeter([]),
            'state': TestMeter([])
        }

        result = self._run_transform(meters)
        self.assertEqual({}, result)

    def test_online_constant_flavor(self):
        """
        Test that a machine online for a 1h period with constant
        flavor works and gives 1h of uptime.
        """
        meters = {
            'flavor': TestMeter([
                {'timestamp': testdata.t0, 'counter_volume': testdata.flavor},
                {'timestamp': testdata.t1, 'counter_volume': testdata.flavor},
                ]),
            'state': TestMeter([
                {'timestamp': testdata.t0, 'counter_volume': states['active']},
                {'timestamp': testdata.t1, 'counter_volume': states['active']}
                ]),
        }

        result = self._run_transform(meters)
        # there should be one hour of usage.
        self.assertEqual({testdata.flavor: 3600}, result)

    def test_offline_constant_flavor(self):
        """
        Test that a machine offline for a 1h period with constant flavor
        works and gives zero uptime.
        """

        meters = {
            'flavor': TestMeter([
                {'timestamp': testdata.t0, 'counter_volume': testdata.flavor},
                {'timestamp': testdata.t1, 'counter_volume': testdata.flavor},
                ]),
            'state': TestMeter([
                {'timestamp': testdata.t0, 'counter_volume': states['stopped']},
                {'timestamp': testdata.t1, 'counter_volume': states['stopped']}
                ]),
        }

        result = self._run_transform(meters)
        # there should be no usage, the machine was off.
        self.assertEqual({}, result)

    def test_shutdown_during_period(self):
        """
        Test that a machine run for 0.5 then shutdown gives 0.5h uptime.
        """
        meters = {
            'flavor': TestMeter([
                {'timestamp': testdata.t0, 'counter_volume': testdata.flavor},
                {'timestamp': testdata.t0_30, 'counter_volume': testdata.flavor},
                {'timestamp': testdata.t1, 'counter_volume': testdata.flavor},
                ]),
            'state': TestMeter([
                {'timestamp': testdata.t0, 'counter_volume': states['active']},
                {'timestamp': testdata.t0_30, 'counter_volume': states['stopped']},
                {'timestamp': testdata.t1, 'counter_volume': states['stopped']}
                ]),
        }

        result = self._run_transform(meters)
        # there should be half an hour of usage.
        self.assertEqual({'m1.tiny': 1800}, result)

    def test_online_flavor_change(self):
        """
        Test that a machine run for 0.5h as m1.tiny, resized to m1.large,
        and run for a further 0.5 yields 0.5h of uptime in each class.
        """
        meters = {
            'flavor': TestMeter([
                {'timestamp': testdata.t0, 'counter_volume': testdata.flavor},
                {'timestamp': testdata.t0_30, 'counter_volume': testdata.flavor2},
                {'timestamp': testdata.t1, 'counter_volume': testdata.flavor2},
                ]),
            'state': TestMeter([
                {'timestamp': testdata.t0, 'counter_volume': states['active']},
                {'timestamp': testdata.t0_30, 'counter_volume': states['active']},
                {'timestamp': testdata.t1, 'counter_volume': states['active']}
                ]),
        }

        result = self._run_transform(meters)
        # there should be half an hour of usage in each of m1.tiny and m1.large
        self.assertEqual({'m1.tiny': 1800, 'm1.large': 1800}, result)

    def test_period_leadin_none_available(self):
        """
        Test that if the first data point is well into the window, and we had no
        lead-in data, we assume no usage until our first real data point.
        """
        meters = {
            'flavor': TestMeter([
                {'timestamp': testdata.t0_10, 'counter_volume': testdata.flavor},
                {'timestamp': testdata.t1, 'counter_volume': testdata.flavor},
                ]),
            'state': TestMeter([
                {'timestamp': testdata.t0_10, 'counter_volume': states['active']},
                {'timestamp': testdata.t1, 'counter_volume': states['active']},
                ]),
        }

        result = self._run_transform(meters)
        # there should be 50 minutes of usage; we have no idea what happened before
        # that so we don't try to bill it.
        self.assertEqual({'m1.tiny': 3000}, result)

    @unittest.skip      # this doesnt work yet
    def test_period_leadin_available(self):
        """
        Test that if the first data point is well into the window, but we *do*
        have lead-in data, then we use the lead-in clipped to the start of the
        window.
        """
        meters = {
            'flavor': TestMeter([
                {'timestamp': testdata.tpre, 'counter_volume': testdata.flavor},
                {'timestamp': testdata.t0_10, 'counter_volume': testdata.flavor},
                {'timestamp': testdata.t1, 'counter_volume': testdata.flavor},
                ]),
            'state': TestMeter([
                {'timestamp': testdata.tpre, 'counter_volume': states['active']},
                {'timestamp': testdata.t0_10, 'counter_volume': states['active']},
                {'timestamp': testdata.t1, 'counter_volume': states['active']},
                ]),
        }

        result = self._run_transform(meters)
        # there should be 60 minutes of usage; we have no idea what happened before
        # that so we don't try to bill it.
        self.assertEqual({'m1.tiny': 3600}, result)

class GaugeMaxTransformerTests(unittest.TestCase):
    def test_wrong_metrics_type(self):
        """
        Test that the correct exception is thrown if any given meters
        are of the wrong type.
        """
        xform = artifice.transformers.GaugeMax()

        meter = mock.MagicMock()
        meter.type = "cumulative"
        
        with self.assertRaises(TransformerValidationError) as e:
            xform.transform_usage({'some_meter': meter}, testdata.ts0, testdata.ts1)

        self.assertTrue(
            e.exception.message.startswith('Meters must all be of type: '))

    def test_all_different_values(self):
        """
        Tests that the transformer correctly grabs the highest value,
        when all values are different.
        """

        meters = {
            'size': TestMeter([
                {'timestamp': testdata.t0, 'counter_volume': 12},
                {'timestamp': testdata.t0_10, 'counter_volume': 3},
                {'timestamp': testdata.t0_20, 'counter_volume': 7},
                {'timestamp': testdata.t0_30, 'counter_volume': 3},
                {'timestamp': testdata.t0_40, 'counter_volume': 25},
                {'timestamp': testdata.t0_50, 'counter_volume': 2},
                {'timestamp': testdata.t1, 'counter_volume': 6},
                ], "gauge")
        }

        xform = artifice.transformers.GaugeMax()
        usage = xform.transform_usage(meters, testdata.ts0, testdata.ts1)

        self.assertEqual({'size': 25}, usage)

    def test_all_same_values(self):
        """
        Tests that that transformer correctly grabs any value,
        when all values are the same.
        """

        meters = {
            'size': TestMeter([
                {'timestamp': testdata.t0, 'counter_volume': 25},
                {'timestamp': testdata.t0_30, 'counter_volume': 25},
                {'timestamp': testdata.t1, 'counter_volume': 25},
                ], "gauge")
        }

        xform = artifice.transformers.GaugeMax()
        usage = xform.transform_usage(meters, testdata.ts0, testdata.ts1)

        self.assertEqual({'size': 25}, usage)


class CumulativeRangeTransformerTests(unittest.TestCase):

    def test_no_reset(self):
        """
        Tests that the correct usage is being returned for the range,
        when no reset occurs.
        """
        meters = {
            'time': TestMeter([
                {'timestamp': testdata.t0, 'counter_volume': 1},
                {'timestamp': testdata.t0_10, 'counter_volume': 2},
                {'timestamp': testdata.t0_20, 'counter_volume': 3},
                {'timestamp': testdata.t0_30, 'counter_volume': 4},
                {'timestamp': testdata.t0_40, 'counter_volume': 5},
                {'timestamp': testdata.t0_50, 'counter_volume': 6},
                {'timestamp': testdata.t1, 'counter_volume': 7},
                ], "cumulative")
        }

        xform = artifice.transformers.CumulativeRange()
        usage = xform.transform_usage(meters, testdata.ts0, testdata.ts1)

        self.assertEqual({'time': 6}, usage)

    def test_clear_reset(self):
        """
        Tests that the correct usage is being returned for the range,
        when a reset occurs.
        """
        meters = {
            'time': TestMeter([
                {'timestamp': testdata.t0, 'counter_volume': 10},
                {'timestamp': testdata.t0_10, 'counter_volume': 20},
                {'timestamp': testdata.t0_20, 'counter_volume': 40},
                {'timestamp': testdata.t0_30, 'counter_volume': 0},
                {'timestamp': testdata.t0_40, 'counter_volume': 20},
                {'timestamp': testdata.t0_50, 'counter_volume': 30},
                {'timestamp': testdata.t1, 'counter_volume': 40},
                ], "cumulative")
        }

        xform = artifice.transformers.CumulativeRange()
        usage = xform.transform_usage(meters, testdata.ts0, testdata.ts1)

        self.assertEqual({'time': 70}, usage)

    def test_close_reset(self):
        """
        Tests that the correct usage is being returned for the range,
        when a very close reset occurs.
        """
        meters = {
            'time': TestMeter([
                {'timestamp': testdata.t0, 'counter_volume': 10},
                {'timestamp': testdata.t0_10, 'counter_volume': 20},
                {'timestamp': testdata.t0_20, 'counter_volume': 40},
                {'timestamp': testdata.t0_30, 'counter_volume': 39},
                {'timestamp': testdata.t0_40, 'counter_volume': 50},
                {'timestamp': testdata.t0_50, 'counter_volume': 60},
                {'timestamp': testdata.t1, 'counter_volume': 70},
                ], "cumulative")
        }

        xform = artifice.transformers.CumulativeRange()
        usage = xform.transform_usage(meters, testdata.ts0, testdata.ts1)

        self.assertEqual({'time': 100}, usage)
