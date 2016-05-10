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

import logging
import sys

import eventlet
from eventlet import wsgi
from oslo_config import cfg
import logging as std_logging
from distil.api import app
from oslo_log import log
from distil import config


CONF = cfg.CONF
LOG = log.getLogger(__name__)


class WritableLogger(object):
    """A thin wrapper that responds to `write` and logs."""

    def __init__(self, LOG, level=std_logging.DEBUG):
        self.LOG = LOG
        self.level = level

    def write(self, msg):
        self.LOG.log(self.level, msg.rstrip("\n"))


def main():
    config.parse_args(sys.argv[1:], 'distil-api')

    application = app.make_app()
    CONF.log_opt_values(LOG, logging.INFO)
    try:
        wsgi.server(eventlet.listen((CONF.host, CONF.port), backlog=500),
                    application, log=WritableLogger(LOG))
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
