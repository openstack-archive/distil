# Copyright 2016 - Catalyst IT
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import datetime
import json
import sqlalchemy
from sqlalchemy import orm as sql_orm
from sqlalchemy import pool
import traceback

from oslo_config import cfg
from oslo_log import log as logging
from oslo_service import periodic_task
from oslo_service import threadgroup

from distil.api import web
from distil import config
from distil import database
from distil import interface as iface
from distil import models

LOG = logging.getLogger(__name__)

CONF = cfg.CONF

_periodic_tasks = {}


class DistilPeriodicTasks(periodic_task.PeriodicTasks):
    @periodic_task.periodic_task(spacing=10, run_immediately=True)
    def collect_usage(self, ctx=None):
        """Run usage collection on all tenants present in Keystone."""
        try:
            LOG.info("Usage collection run started.")

            # global engine
            # engine = sqlalchemy.create_engine(config.main["database_uri"],
            #                                   poolclass=pool.NullPool)
            # global Session
            # Session = sql_orm.scoped_session(
            #     lambda: sql_orm.create_session(bind=engine))
            #
            # session = Session()
            # interface = iface.Interface()
            # tenants = interface.tenants
            # reset_cache()
            # db = database.Database(session)
            # end = datetime.datetime.utcnow().replace(minute=0, second=0,
            #                                          microsecond=0)
            # resp = {"tenants": [], "errors": 0}
            # run_once = False
            #
            # for tenant in tenants:
            #     if web.collect_usage(tenant, db, session, resp, end):
            #         run_once = True
            #
            # if (run_once):
            #     session.begin()
            #     last_run = session.query(models._Last_Run)
            #     if last_run.count() == 0:
            #         last_run = models._Last_Run(last_run=end)
            #         session.add(last_run)
            #         session.commit()
            #     else:
            #         last_run[0].last_run = end
            #         session.commit()
            # session.close()

            LOG.info("Usage collection run complete.")
            # LOG.info("resp: %s", json.dumps(resp))
        except Exception as e:
            trace = traceback.format_exc()
            LOG.critical('Exception escaped! %s \nTrace: \n%s' % (e, trace))


def setup():
    tg = threadgroup.ThreadGroup()
    pt = DistilPeriodicTasks(CONF)

    tg.add_dynamic_timer(
        pt.run_periodic_tasks,
        initial_delay=None,
        periodic_interval_max=5,
        context=None
    )

    _periodic_tasks[pt] = tg

    return tg


def stop_all_periodic_tasks():
    for pt, tg in _periodic_tasks.items():
        tg.stop()
        del _periodic_tasks[pt]
