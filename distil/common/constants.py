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

from datetime import datetime

# Date format Ceilometer uses
# 2013-07-03T13:34:17
# which is, as an strftime:
# timestamp = datetime.strptime(res["timestamp"], "%Y-%m-%dT%H:%M:%S.%f")
# or
# timestamp = datetime.strptime(res["timestamp"], "%Y-%m-%dT%H:%M:%S")

# Most of the time we use date_format
date_format = "%Y-%m-%dT%H:%M:%S"


# Sometimes things also have milliseconds, so we look for that too.
# Because why not be annoying in all the ways?
date_format_f = "%Y-%m-%dT%H:%M:%S.%f"

# Some useful constants
iso_time = "%Y-%m-%dT%H:%M:%S"
iso_date = "%Y-%m-%d"
dawn_of_time = datetime(2016, 5, 10)

# VM states:
states = {'active': 1,
          'building': 2,
          'paused': 3,
          'suspended': 4,
          'stopped': 5,
          'rescued': 6,
          'resized': 7,
          'soft_deleted': 8,
          'deleted': 9,
          'error': 10,
          'shelved': 11,
          'shelved_offloaded': 12}

RATE_DIGITS = 6
PRICE_DIGITS = 2
