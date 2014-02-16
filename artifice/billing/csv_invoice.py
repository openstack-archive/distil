import os
from csv import writer
from artifice import invoice
from artifice import clerk_mixins
import yaml
from decimal import *


class Csv(clerk_mixins.ClerkRatesMixin, invoice.Invoice):

    def __init__(self, tenant, start, end, config):
        self.config = config
        self.tenant = tenant
        self.lines = {}
        self.closed = False
        self.start = start
        self.end = end
        self.total = Decimal(0.0)

    def bill(self):
        # Usage is one of VMs, Storage, or Volumes.
        for element in self.tenant.resources.values():
            print " * " + element.metadata['type']

            print "   - resource id: " + str(element.id)
            self.add_line(element.metadata['type'], [element.id])

            appendee = []
            appendee2 = []
            for key, value in element.metadata.iteritems():
                print "   - " + key + ": " + str(value)
                appendee.append(key + str(":"))
                appendee2.append(value)

            self.add_line(element.metadata['type'], appendee)
            self.add_line(element.metadata['type'], appendee2)

            total_cost = Decimal(0.0)
            appendee = ["service:", "usage:", "rate:", "cost:"]
            self.add_line(element.metadata['type'], appendee)
            for strategy in element.usage_strategies.values():
                appendee = []
                cost = Decimal(0.0)
                usage = Decimal(strategy.volume)

                # GET REGION FROM CONFIG:
                region = 'wellington'

                rate = self.rate(strategy.service, region)
                cost = usage * rate
                total_cost += cost
                appendee.append(strategy.service)
                appendee.append(usage)
                appendee.append(rate)
                appendee.append(round(cost, 2))
                print "   - " + strategy.service + ": " + str(usage)
                print "     - rate: " + str(rate)
                print "     - cost: " + str(round(cost))
                self.add_line(element.metadata['type'], appendee)
            appendee = ["total cost:", round(total_cost, 2)]
            self.add_line(element.metadata['type'], appendee)
            print "   - total cost: " + str(round(total_cost))

            self.add_line(element.metadata['type'], [])
            self.total += total_cost

    def add_line(self, el_type, line):
        if not self.closed:
            try:
                self.lines[el_type].append(line)
            except KeyError:
                self.lines[el_type] = [line]
            return
        raise AttributeError("Can't add to a closed invoice")

    @property
    def filename(self):
        fn_dict = dict(tenant=self.tenant.name, start=self.start,
                       end=self.end)

        fn = os.path.join(
            self.config["output_path"],
            self.config["output_file"] % fn_dict
        )
        return fn

    def close(self):
        try:
            open(self.filename)
            raise RuntimeError("Can't write to an existing file!")
        except IOError:
            pass
        fh = open(self.filename, "w")
        csvwriter = writer(fh, dialect='excel', delimiter=',')

        csvwriter.writerow(["", "from", "until"])
        csvwriter.writerow(["usage range: ", str(self.start), str(self.end)])
        csvwriter.writerow([])

        for key in self.lines:
            for line in self.lines[key]:
                csvwriter.writerow(line)
            csvwriter.writerow([])

        # write a blank line
        csvwriter.writerow([])
        # write total
        csvwriter.writerow(["invoice total cost: ", round(self.total, 2)])

        fh.close()
        self.closed = True
