# Copyright 2014 Catalyst IT Ltd
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

from oslo_config import cfg

from stevedore import driver

CONF = cfg.CONF
RATER = None

class BaseRater(object):

    def __init__(self, conf=None):
        self.conf = conf

    def rate(self, name, region=None):
        raise NotImplementedError("Not implemented in base class")


def get_rater():
    if RATER == None:
        RATER = driver.DriverManager('distil.rater',
                                 CONF.rater.rater_type,
                                 invoke_on_load=True,
                                 invoke_kwds={}).driver
    return RATER