# Copyright (c) 2014 Catalyst IT Ltd
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

from distil.utils import general


class BaseTransformer(object):

    def __init__(self):
        self.config = general.get_collector_config()['transformers']

    def transform_usage(self, meter_name, raw_data, start_at, end_at):
        return self._transform_usage(meter_name, raw_data, start_at, end_at)

    def _transform_usage(self, meter_name, raw_data, start_at, end_at):
        raise NotImplementedError
