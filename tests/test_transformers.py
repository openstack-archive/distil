import artifice.transformers
import artifice.constants
import unittest
import mock

class testdata:
    t0 = '2014-01-01T00:00:00'
    t1 = '2014-01-01T01:00:00'
    flavor = 'm1.tiny'

    t0_30 = '2014-01-01T00:30:00'
    flavor2 = 'm1.large'

class TestMeter(object):
    def __init__(self, data):
        self.data = data
    def usage(self):
        return self.data

class UptimeTransformerTests(unittest.TestCase):
    def test_required_metrics_not_present(self):
        """
        Test that the correct exception is thrown if one of the required meters
        is not present.
        """
        xform = artifice.transformers.Uptime()
        
        with self.assertRaises(AttributeError) as e:
            xform.transform_usage({})

        self.assertTrue(e.exception.message.startswith('Required meters:'))

    def _run_transform(self, meters):
        xform = artifice.transformers.Uptime()
        with mock.patch('artifice.helpers.flavor_name') as flavor_name:
            flavor_name.side_effect = lambda x: x
            return xform.transform_usage(meters)

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
                {'timestamp': testdata.t0, 'counter_volume': artifice.constants.active},
                {'timestamp': testdata.t1, 'counter_volume': artifice.constants.active}
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
        xform = artifice.transformers.Uptime()

        meters = {
            'flavor': TestMeter([
                {'timestamp': testdata.t0, 'counter_volume': testdata.flavor},
                {'timestamp': testdata.t1, 'counter_volume': testdata.flavor},
                ]),
            'state': TestMeter([
                {'timestamp': testdata.t0, 'counter_volume': artifice.constants.stopped},
                {'timestamp': testdata.t1, 'counter_volume': artifice.constants.stopped}
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
                {'timestamp': testdata.t0, 'counter_volume': artifice.constants.active},
                {'timestamp': testdata.t0_30, 'counter_volume': artifice.constants.stopped},
                {'timestamp': testdata.t1, 'counter_volume': artifice.constants.stopped}
                ]),
        }

        result = self._run_transform(meters)
        # there should be half an hour of usage.
        self.assertEqual({'m1.tiny': 1800}, result)

    def test_online_flavor_change(self):
        """
        Test that a machine run for 0.5h as m1.tiny, resized to m1.large, and run
        for a further 0.5 yields 0.5h of uptime in each class.
        """
        meters = {
            'flavor': TestMeter([
                {'timestamp': testdata.t0, 'counter_volume': testdata.flavor},
                {'timestamp': testdata.t0_30, 'counter_volume': testdata.flavor2},
                {'timestamp': testdata.t1, 'counter_volume': testdata.flavor2},
                ]),
            'state': TestMeter([
                {'timestamp': testdata.t0, 'counter_volume': artifice.constants.active},
                {'timestamp': testdata.t0_30, 'counter_volume': artifice.constants.active},
                {'timestamp': testdata.t1, 'counter_volume': artifice.constants.active}
                ]),
        }

        result = self._run_transform(meters)
        # there should be half an hour of usage in each of m1.tiny and m1.large
        self.assertEqual({'m1.tiny': 1800, 'm1.large': 1800}, result)
