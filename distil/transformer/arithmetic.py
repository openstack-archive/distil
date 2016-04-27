# Copyright (c) 2013 Mirantis Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime

from distil.transformer import BaseTransformer


class MaxTransformer(BaseTransformer):
    """Transformer for max-integration of a gauge value over time.
    If the raw unit is 'gigabytes', then the transformed unit is
    'gigabyte-hours'.
    """

    def _transform_usage(self, meter_name, raw_data, start_at, end_at):
        max_vol = max([v["counter_volume"]
                       for v in raw_data]) if len(raw_data) else 0
        hours = (end_at - start_at).total_seconds() / 3600.0
        return {meter_name: max_vol * hours}


class SumTransformer(BaseTransformer):
    """Transformer for sum-integration of a gauge value for given period.
    """
    def _transform_usage(self, meter_name, raw_data, start_at, end_at):
        sum_vol = 0
        for sample in raw_data:
            t = datetime.datetime.strptime(sample['timestamp'],
                                           '%Y-%m-%dT%H:%M:%S.%f')
            if t >= start_at and t < end_at:
                sum_vol += sample["counter_volume"]
        return {meter_name: sum_vol}
