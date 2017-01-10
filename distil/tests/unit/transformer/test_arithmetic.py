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

import datetime

import mock

from distil.common.constants import date_format
from distil.common import general
from distil.tests.unit import base
from distil.transformer import arithmetic

p = lambda t: datetime.datetime.strptime(t, date_format)


class FAKE_DATA:
    t0 = p('2014-01-01T00:00:00')
    t0_10 = p('2014-01-01T00:10:00')
    t0_20 = p('2014-01-01T00:30:00')
    t0_30 = p('2014-01-01T00:30:00')
    t0_40 = p('2014-01-01T00:40:00')
    t0_50 = p('2014-01-01T00:50:00')
    t1 = p('2014-01-01T01:00:00')


@mock.patch.object(general, 'get_transformer_config', mock.Mock())
class TestMaxTransformer(base.DistilTestCase):
    def test_all_different_values(self):
        """
        Tests that the transformer correctly grabs the highest value,
        when all values are different.
        """

        data = [
            {'timestamp': FAKE_DATA.t0, 'volume': 12},
            {'timestamp': FAKE_DATA.t0_10, 'volume': 3},
            {'timestamp': FAKE_DATA.t0_20, 'volume': 7},
            {'timestamp': FAKE_DATA.t0_30, 'volume': 3},
            {'timestamp': FAKE_DATA.t0_40, 'volume': 25},
            {'timestamp': FAKE_DATA.t0_50, 'volume': 2},
            {'timestamp': FAKE_DATA.t1, 'volume': 6},
        ]

        xform = arithmetic.MaxTransformer()
        usage = xform.transform_usage('some_meter', data, FAKE_DATA.t0,
                                      FAKE_DATA.t1)

        self.assertEqual({'some_meter': 25}, usage)

    def test_all_same_values(self):
        """
        Tests that that transformer correctly grabs any value,
        when all values are the same.
        """

        data = [
            {'timestamp': FAKE_DATA.t0, 'volume': 25},
            {'timestamp': FAKE_DATA.t0_30, 'volume': 25},
            {'timestamp': FAKE_DATA.t1, 'volume': 25},
        ]

        xform = arithmetic.MaxTransformer()
        usage = xform.transform_usage('some_meter', data, FAKE_DATA.t0,
                                      FAKE_DATA.t1)

        self.assertEqual({'some_meter': 25}, usage)

    def test_none_value(self):
        """
        Tests that that transformer correctly handles a None value.
        """

        data = [
            {'timestamp': FAKE_DATA.t0, 'volume': None},
        ]

        xform = arithmetic.MaxTransformer()
        usage = xform.transform_usage('some_meter', data, FAKE_DATA.t0,
                                      FAKE_DATA.t1)

        self.assertEqual({'some_meter': 0}, usage)

    def test_none_and_other_values(self):
        """
        Tests that that transformer correctly handles a None value.
        """

        data = [
            {'timestamp': FAKE_DATA.t0, 'volume': None},
            {'timestamp': FAKE_DATA.t0_30, 'volume': 25},
            {'timestamp': FAKE_DATA.t1, 'volume': 27},
        ]

        xform = arithmetic.MaxTransformer()
        usage = xform.transform_usage('some_meter', data, FAKE_DATA.t0,
                                      FAKE_DATA.t1)

        self.assertEqual({'some_meter': 27}, usage)


@mock.patch.object(general, 'get_transformer_config', mock.Mock())
class TestStorageMaxTransformer(unittest.TestCase):
    def test_all_different_values(self):
        """
        Tests that the transformer correctly grabs the highest value,
        when all values are different.
        """

        data = [
            {'timestamp': FAKE_DATA.t0, 'volume': 12,
             'metadata': {}},
            {'timestamp': FAKE_DATA.t0_10, 'volume': 3,
             'metadata': {}},
            {'timestamp': FAKE_DATA.t0_20, 'volume': 7,
             'metadata': {}},
            {'timestamp': FAKE_DATA.t0_30, 'volume': 3,
             'metadata': {}},
            {'timestamp': FAKE_DATA.t0_40, 'volume': 25,
             'metadata': {}},
            {'timestamp': FAKE_DATA.t0_50, 'volume': 2,
             'metadata': {}},
            {'timestamp': FAKE_DATA.t1, 'volume': 6,
             'metadata': {}},
        ]

        xform = arithmetic.StorageMaxTransformer()
        usage = xform.transform_usage('some_meter', data, FAKE_DATA.t0,
                                      FAKE_DATA.t1)

        self.assertEqual({'some_meter': 25}, usage)

    def test_all_same_values(self):
        """
        Tests that that transformer correctly grabs any value,
        when all values are the same.
        """

        data = [
            {'timestamp': FAKE_DATA.t0, 'volume': 25,
             'metadata': {}},
            {'timestamp': FAKE_DATA.t0_30, 'volume': 25,
             'metadata': {}},
            {'timestamp': FAKE_DATA.t1, 'volume': 25,
             'metadata': {}},
        ]

        xform = arithmetic.StorageMaxTransformer()
        usage = xform.transform_usage('some_meter', data, FAKE_DATA.t0,
                                      FAKE_DATA.t1)

        self.assertEqual({'some_meter': 25}, usage)

    def test_none_value(self):
        """
        Tests that that transformer correctly handles a None value.
        """

        data = [
            {'timestamp': FAKE_DATA.t0, 'volume': None,
             'metadata': {}},
        ]

        xform = arithmetic.StorageMaxTransformer()
        usage = xform.transform_usage('some_meter', data, FAKE_DATA.t0,
                                      FAKE_DATA.t1)

        self.assertEqual({'some_meter': 0}, usage)

    def test_none_and_other_values(self):
        """
        Tests that that transformer correctly handles a None value.
        """

        data = [
            {'timestamp': FAKE_DATA.t0, 'volume': None,
             'metadata': {}},
            {'timestamp': FAKE_DATA.t0_30, 'volume': 25,
             'metadata': {}},
            {'timestamp': FAKE_DATA.t1, 'volume': 27,
             'metadata': {}},
        ]

        xform = arithmetic.StorageMaxTransformer()
        usage = xform.transform_usage('some_meter', data, FAKE_DATA.t0,
                                      FAKE_DATA.t1)

        self.assertEqual({'some_meter': 27}, usage)


@mock.patch.object(general, 'get_transformer_config', mock.Mock())
class TestSumTransformer(unittest.TestCase):
    def test_basic_sum(self):
        """
        Tests that the transformer correctly calculate the sum value.
        """

        data = [
            {'timestamp': p('2014-01-01T00:00:00'), 'volume': 1},
            {'timestamp': p('2014-01-01T00:10:00'), 'volume': 1},
            {'timestamp': p('2014-01-01T01:00:00'), 'volume': 1},
        ]

        xform = arithmetic.SumTransformer()
        usage = xform.transform_usage('fake_meter', data, FAKE_DATA.t0,
                                      FAKE_DATA.t1)

        self.assertEqual({'fake_meter': 2}, usage)

    def test_none_value(self):
        """
        Tests that that transformer correctly handles a None value.
        """

        data = [
            {'timestamp': FAKE_DATA.t0, 'volume': None},
        ]

        xform = arithmetic.SumTransformer()
        usage = xform.transform_usage('some_meter', data, FAKE_DATA.t0,
                                      FAKE_DATA.t1)

        self.assertEqual({'some_meter': 0}, usage)

    def test_none_and_other_values(self):
        """
        Tests that that transformer correctly handles a None value.
        """

        data = [
            {'timestamp': FAKE_DATA.t0, 'volume': None},
            {'timestamp': FAKE_DATA.t0_30, 'volume': 25},
            {'timestamp': FAKE_DATA.t0_50, 'volume': 25},
        ]

        xform = arithmetic.SumTransformer()
        usage = xform.transform_usage('some_meter', data, FAKE_DATA.t0,
                                      FAKE_DATA.t1)

        self.assertEqual({'some_meter': 50}, usage)
