# Copyright 2016 Catalyst IT Ltd
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

from oslo_config import cfg
from oslo_log import log as logging
from oslo_service import service
from oslo_service import threadgroup
from stevedore import driver

from distil import constants

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class CollectorService(service.Service):
    def __init__(self):
        super(CollectorService, self).__init__()

        self.thread_grp = None

        collector_args = {}
        self.collector = driver.DriverManager(
            constants.COLLECTORS_NAMESPACE,
            CONF.collector.collector_backend,
            invoke_on_load=True,
            invoke_kwds=collector_args).driver

    def start(self):
        LOG.info("Starting collector service...")

        self.thread_grp = threadgroup.ThreadGroup()
        self.thread_grp.add_timer(CONF.collector.periodic_interval,
                                  self.collect_usage)

        super(CollectorService, self).start()
        LOG.info("Collector service started.")

    def stop(self):
        LOG.info("Stopping collector service gracefully...")

        self.thread_grp.stop()
        super(CollectorService, self).stop()

        LOG.info("Collector service stoped.")

    def reset(self):
        super(CollectorService, self).reset()
        logging.setup(CONF, 'distil-collector')

    def collect_usage(self):
        LOG.info("Begin to collect usage...")
