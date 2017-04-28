# Copyright (c) 2016 Catalyst IT Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License.  You may obtain a copy
# of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.

import copy
import six


from oslo_log import log
from stevedore import driver

from distil import exceptions

LOG = log.getLogger(__name__)
_ERP_DRIVER = None


def load_erp_driver(conf):
    """Loads a erp driver and returns it.

    :param conf: Configuration instance to use for loading the
        driver. Must include a 'drivers' group.
    """

    global _ERP_DRIVER

    if not _ERP_DRIVER:
        _invoke_args = [conf]

        try:
            mgr = driver.DriverManager('distil.erp',
                                       conf.erp_driver,
                                       invoke_on_load=True,
                                       invoke_args=_invoke_args)

            _ERP_DRIVER = mgr.driver

        except Exception as exc:
            LOG.exception(exc)
            raise exceptions.InvalidDriver(
                'Failed to load ERP driver for {0}'.format(conf.erp_driver)
            )

    return _ERP_DRIVER
