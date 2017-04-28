# Copyright 2014 Catalyst IT Ltd.
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

from distil.i18n import _

# FIXME(flwang): configration?
_FATAL_EXCEPTION_FORMAT_ERRORS = False


class DistilException(Exception):
    """Base Exception for the project

    To correctly use this class, inherit from it and define
    a 'message' and 'code' properties.
    """
    message = _("An unknown exception occurred")
    code = 500

    def __str__(self):
        return self.message

    def __init__(self, message=None):
        if message is not None:
            self.message = message

        super(DistilException, self).__init__(
            '%s: %s' % (self.code, self.message))


class IncorrectStateError(DistilException):
    message = _("Incorrect state.")


class NotFoundException(DistilException):
    code = 404
    message = _("Object not found.")


class DuplicateException(DistilException):
    code = 409
    message = _("An object with the same identifier already exists.")


class InvalidConfig(DistilException):
    message = _("Invalid configuration.")


class DBException(DistilException):
    message = _("Database exception.")


class MalformedRequestBody(DistilException):
    code = 400
    message = _("Malformed message body.")


class DateTimeException(DistilException):
    code = 400
    message = _("An unexpected date, date format, or date range was given.")


class Forbidden(DistilException):
    code = 403
    message = _("You are not authorized to complete this action")


class InvalidDriver(DistilException):
    """A driver was not found or loaded."""
    message = _("Failed to load driver")

class ERPException(DistilException):
    code = 500
    message = _("ERP server error.")
