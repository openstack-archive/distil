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
    """Base Distil Exception

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.
    """

    msg_fmt = _("An unknown exception occurred.")

    def __init__(self, message=None, **kwargs):
        self.kwargs = kwargs

        if 'code' not in self.kwargs:
            try:
                self.kwargs['code'] = self.code
            except AttributeError:
                pass

        if not message:
            try:
                message = self.msg_fmt % kwargs
            except KeyError:
                exc_info = sys.exc_info()
                if _FATAL_EXCEPTION_FORMAT_ERRORS:
                    raise exc_info[0], exc_info[1], exc_info[2]
                else:
                    message = self.msg_fmt

        super(DistilException, self).__init__(message)

    def format_message(self):
        if self.__class__.__name__.endswith('_Remote'):
            return self.args[0]
        else:
            return unicode(self)


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
