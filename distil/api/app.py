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
import flask
from oslo_config import cfg
from oslo_log import log

from distil.api import auth
from distil.api import acl
from distil.api import v2 as api_v2
from distil import config
from distil.utils import api
from distil.utils import cache

CONF = cfg.CONF
LOG = log.getLogger('__main__')


def make_app(args=None):
    config.parse_args(args, 'distil-api')

    app = flask.Flask(__name__)

    @app.route('/', methods=['GET'])
    def version_list():
        return api.render({
            "versions": [
                {"id": "v2", "status": "CURRENT"}
            ]})

    app.register_blueprint(api_v2.rest, url_prefix="/v2")
    app.wsgi_app = auth.wrap(app.wsgi_app, CONF)

    acl.setup_policy()
    cache.setup_cache(CONF)

    if CONF.debug:
        CONF.log_opt_values(LOG, log.DEBUG)
    return app
