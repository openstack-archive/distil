# Copyright 2014 Catalyst IT Ltd
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

import sys

from oslo_config import cfg
from oslo_log import log as logging
from oslo_service import service

from distil import config
from distil.service import collector


def main():
    config.parse_args(sys.argv[1:], 'distil-collector')

    srv = collector.CollectorService()
    launcher = service.launch(cfg.CONF, srv, restart_method='mutate')
    launcher.wait()


if __name__ == '__main__':
    main()
