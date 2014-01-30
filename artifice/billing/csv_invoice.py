import os
from csv import writer
from artifice import invoice
import yaml
from decimal import *


class Csv(invoice.RatesFileMixin, invoice.NamesFileMixin, invoice.Invoice):

    def __init__(self, tenant, start, end, config):
        self.config = config
        self.tenant = tenant
        self.lines = {}
        self.closed = False
        self.start = start
        self.end = end

    def bill(self, usage):
        # Usage is one of VMs, Storage, or Volumes.
        for element in usage:
            appendee = []
            print " * " + element.type

            for field in self.config["models"][element.type]["info_fields"]:
                try:
                    value = element.get(field)
                    print "   - " + field + ": " + str(value)
                    appendee.append(value)
                except AttributeError:
                    appendee.append("")

            cost = Decimal(0.0)
            for key in self.config["models"][element.type]["strategies"]:
                strategy = element.usage_strategies[key]
                usage = element.get(strategy['usage'])
                try:
                    rate = self.rate(element.get(strategy['rate']))
                except AttributeError:
                    rate = self.rate(strategy['rate'])
                cost += usage * rate
                appendee.append(usage)
                appendee.append(rate)
                print "   - " + key + ": " + str(usage)
                print "     - rate: " + str(rate)
            appendee.append(cost)
            print "   - cost: " + str(cost)

            # print appendee
            self.add_line(element.type, appendee)

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
        fn_dict = dict(tenant=self.tenant.tenant['name'], start=self.start,
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
            csvwriter.writerow([key + ":"])
            csvwriter.writerow(self.build_headers(key))
            for line in self.lines[key]:
                csvwriter.writerow(line)
            csvwriter.writerow([])

        # write a blank line
        csvwriter.writerow([])
        # write total
        csvwriter.writerow(["total cost: ", self.total()])

        fh.close()
        self.closed = True

    def build_headers(self, el_type):
        headers = list(self.config["models"][el_type]["info_fields"])
        for strat in self.config["models"][el_type]["strategies"]:
            headers.append(strat)
            headers.append(strat + " rate")
        headers.append("cost")
        return headers

    def total(self):
        total = Decimal(0.0)
        for key in self.lines:
            for line in self.lines[key]:
                try:
                    # cost will always be the final value in the line.
                    total += Decimal(line[len(line) - 1])
                except (TypeError, ValueError):
                    total += 0
        return total
