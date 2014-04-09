from decimal import Decimal
import csv


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
                fh = open(self.config["file"])
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
                    raise IndexError("malformed rates CSV!")
                fh.close()
            except KeyError:
                # couldn't actually find the useful info for rateS?
                print "Couldn't find rates info configuration option!"
                raise
            except IndexError:
                raise IndexError("Malformed rates CSV!")
            except IOError:
                print "Couldn't open the file!"
                raise
        return {'rate': self.__rates[name]["rate"],
                'unit': self.__rates[name]["unit"]}
