from decimal import Decimal
import csv
import logging as log


class RatesManager(object):

    def __init__(self, config):
        self.config = config

    def rate(self, name, region=None):
        raise NotImplementedError("Not implemented in base class")


class RatesFile(RatesManager):
    def __init__(self, config):
        super(RatesFile, self).__init__(config)

        try:
            with open(self.config['file']) as fh:
                # Makes no opinions on the file structure
                reader = csv.reader(fh, delimiter="|")
                self.__rates = {
                    row[1].strip() : {
                        'rate': Decimal(row[3].strip()),
                        'region': row[0].strip(),
                        'unit': row[2].strip()
                    } for row in reader
                }
        except Exception as e:
            log.critical('Failed to load rates file: `%s`' % e)
            raise

    def rate(self, name, region=None):
        return {
            'rate': self.__rates[name]['rate'],
            'unit': self.__rates[name]['unit']
        }
