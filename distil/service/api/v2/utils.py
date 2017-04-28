# Copyright (c) 2017 Catalyst IT Ltd.
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
from datetime import datetime

from distil.common import constants
from distil.db import api as db_api
from distil import exceptions


def convert_project_and_range(project_id, start, end):
    now = datetime.utcnow()

    try:
        if start is not None:
            try:
                start = datetime.strptime(start, constants.iso_date)
            except ValueError:
                start = datetime.strptime(start, constants.iso_time)
        else:
            raise exceptions.DateTimeException(
                message=(
                    "Missing parameter:" +
                    "'start' in format: y-m-d or y-m-dTH:M:S"))
        if not end:
            end = now
        else:
            try:
                end = datetime.strptime(end, constants.iso_date)
            except ValueError:
                end = datetime.strptime(end, constants.iso_time)

            if end > now:
                end = now
    except ValueError:
        raise exceptions.DateTimeException(
            message=(
                "Missing parameter: " +
                "'end' in format: y-m-d or y-m-dTH:M:S"))

    if end <= start:
        raise exceptions.DateTimeException(
            message="End date must be greater than start.")

    if not project_id:
        raise exceptions.NotFoundException("Missing parameter: project_id")

    valid_project = db_api.project_get(project_id)

    return valid_project, start, end
