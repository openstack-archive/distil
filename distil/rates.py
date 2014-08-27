# Copyright (C) 2014 Catalyst IT Ltd
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

from decimal import Decimal
import csv
import logging as log


class RatesManager(object):

    def __init__(self, config):
        self.config = config

    def rate(self, name, region=None):
        raise NotImplementedError("Not implemented in base class")


class RatesFile(RatesManager):
    def rate(self, name, region=None):
        try:
            self.__rates
        except AttributeError:
            self.__rates = {}
        if not self.__rates:
            self.__rates = {}
            try:
                with open(self.config['file']) as fh:
                    # Makes no opinions on the file structure
                    reader = csv.reader(fh, delimiter="|")
                    for row in reader:
                        # The default layout is expected to be:
                        # location | rate name | rate measurement | rate value
                        self.__rates[row[1].strip()] = {
                            "rate": Decimal(row[3].strip()),
                            "region": row[0].strip(),
                            "unit": row[2].strip()
                        }
                    if not self.__rates:
                        raise IndexError("Malformed rates CSV!")
            except KeyError:
                # couldn't actually find the useful info for rates?
                log.critical("Couldn't find rates info configuration option!")
                raise
            except IndexError:
                raise IndexError("Malformed rates CSV!")
            except IOError:
                log.critical("Couldn't open the file!")
                raise
        return {'rate': self.__rates[name]["rate"],
                'unit': self.__rates[name]["unit"]}
