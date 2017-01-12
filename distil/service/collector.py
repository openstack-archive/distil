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

from datetime import datetime

from oslo_config import cfg
from oslo_log import log as logging
from oslo_service import service
from oslo_service import threadgroup
from stevedore import driver

from distil.db import api as db_api
from distil import exceptions
from distil.common import openstack

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


def filter_projects(projects):
    p_filtered = list()

    if CONF.collector.include_tenants:
        p_filtered = [p for p in projects if
                      p['name'] in CONF.collector.include_tenants]
    elif CONF.collector.ignore_tenants:
        p_filtered = [p for p in projects if
                      p['name'] not in CONF.collector.ignore_tenants]
    else:
        p_filtered = projects

    LOG.info("After filtering, %s project(s) left." % len(p_filtered))

    return p_filtered


class CollectorService(service.Service):
    def __init__(self):
        super(CollectorService, self).__init__()

        self.thread_grp = None

        self.validate_config()

        collector_args = {}
        self.collector = driver.DriverManager(
            'distil.collector',
            CONF.collector.collector_backend,
            invoke_on_load=True,
            invoke_kwds=collector_args).driver

    def validate_config(self):
        include_tenants = set(CONF.collector.include_tenants)
        ignore_tenants = set(CONF.collector.ignore_tenants)

        if include_tenants & ignore_tenants:
            raise exceptions.InvalidConfig(
                "Duplicate tenants config in include_tenants and "
                "ignore_tenants."
            )

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
        LOG.info("Begin to collect usage for all projects...")

        projects = filter_projects(openstack.get_projects())

        end = datetime.utcnow().replace(minute=0, second=0, microsecond=0)

        for project in projects:
            # Add a project or get last_collected of existing project.
            db_project = db_api.project_add(project)
            start = db_project.last_collected

            self.collector.collect_usage(project, start, end)
