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

from oslo_utils import uuidutils
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
    code = "UNKNOWN_EXCEPTION"

    def __str__(self):
        return self.message

    def __init__(self):
        super(DistilException, self).__init__(
            '%s: %s' % (self.code, self.message))
        self.uuid = uuidutils.generate_uuid()
        self.message = (_('%(message)s\nError ID: %(id)s')
                        % {'message': self.message, 'id': self.uuid})


class IncorrectStateError(DistilException):
    code = "INCORRECT_STATE_ERROR"

    def __init__(self, message):
        self.message = message


class NotFoundException(DistilException):
    message = _("Object '%s' is not found")
    value = None

    def __init__(self, value, message=None):
        self.code = "NOT_FOUND"
        self.value = value
        if message:
            self.message = message % value


class DuplicateException(DistilException):
    message = _("An object with the same identifier already exists.")


class InvalidConfig(DistilException):
    message = _("Invalid configuration file. %(error_msg)s")


class DBException(DistilException):
    message = _("Database exception.")


class MalformedRequestBody(DistilException):
    message = _("Malformed message body: %(reason)s")

    def __init__(self, reason):
        formatted_message = self.message % {"reason": reason}
        super(MalformedRequestBody, self).__init__(formatted_message)


class DateTimeException(DistilException):
    message = _("An unexpected date, date format, or date range was given.")

    def __init__(self, message=None):
        self.code = 400
        self.message = message


class Forbidden(DistilException):
    code = "FORBIDDEN"
    message = _("You are not authorized to complete this action")


class InvalidDriver(DistilException):
    """A driver was not found or loaded."""
