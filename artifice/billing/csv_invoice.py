import os
from csv import writer
from artifice import invoice
import yaml
from decimal import *


class Csv(invoice.RatesFileMixin, invoice.NamesFileMixin, invoice.Invoice):

    def __init__(self, tenant, start, end, config):
        self.config = config
        self.tenant = tenant
        self.lines = []
        self.closed = False
        self.start = start
        self.end = end
        # This has been moved to the mixin
        # try:
        #     fh = open(config["rates"][ "file" ])
        #     self.costs = yaml.load( fh.read() )
        #     fh.close()
        # except IOError:
        #     # That's problem
        #     print "couldn't load %s" % config["rates_file"]
        #     raise
        # except KeyError:
        #     # Couldn't find it!
        #     print "Missing rates_file in config!"
        #     raise

    def bill(self, usage):
        # Usage is one of VMs, Storage, or Volumes.
        for element in usage:
            appendee = []
            for key in self.config["row_layout"][element.type]:
                if element.type is "vm":
                    if key == "flavor":
                        appendee.append(element.get(key))
                        continue
                    if key == "cost":
                        cost = (element.uptime.volume() *
                                self.rate(element.flavor))
                        appendee.append(cost)
                        print ("flavor: " + element.get("flavor"))
                        print " - name : " + str(element.get("name"))
                        print "   - usage: " + str(element.uptime.volume())
                        print ("   - rate: " +
                               str(self.rate(element.flavor)))
                        print " - cost: " + str(cost)
                        continue
                    if key == "rate":
                        appendee.append(self.rate(element.flavor))
                        continue

                if element.type is "ip":
                    if key == "cost":
                        cost = element.duration * self.rate("ip.floating")
                        appendee.append(cost)
                        print "id: "
                        print " - usage: " + str(element.duration)
                        print ("   - rate: " +
                               str(self.rate("ip.floating")))
                        print " - cost: " + str(cost)
                        continue
                    if key == "rate":
                        appendee.append(self.rate("ip.floating"))
                        continue

                if element.type is "object":
                    if key == "cost":
                        cost = element.size * self.rate("storage.objects.size")
                        appendee.append(cost)
                        print "id:"
                        print " - usage: " + str(element.size)
                        print ("   - rate: " +
                               str(self.rate("storage.objects.size")))
                        print " - cost: " + str(cost)
                        continue
                    if key == "rate":
                        appendee.append(self.rate("storage.objects.size"))
                        continue

                if element.type is "volume":
                    if key == "cost":
                        cost = element.size * self.rate("volume.size")
                        appendee.append(cost)
                        print "id:"
                        print " - usage: " + str(element.size)
                        print ("   - rate: " +
                               str(self.rate("volume.size")))
                        print " - cost: " + str(cost)
                        continue
                    if key == "rate":
                        appendee.append(self.rate("volume.size"))
                        continue

                if element.type is "network":
                    if key == "cost":
                        cost_in = (element.incoming *
                                   self.rate("network.outgoing.bytes"))
                        cost_out = (element.outgoing *
                                    self.rate("network.outgoing.bytes"))
                        print "id:"
                        print " - incoming: " + str(element.incoming)
                        print ("   - rate: " +
                               str(self.rate("network.incoming.bytes")))
                        print " - outgoing: " + str(element.outgoing)
                        print ("   - rate: " +
                               str(self.rate("network.outgoing.bytes")))
                        print " - cost: " + str(cost_in + cost_out)
                        appendee.append(cost_in + cost_out)
                        continue
                    if key == "incoming_rate":
                        appendee.append(self.rate("network.incoming.bytes"))
                        continue
                    if key == "outgoing_rate":
                        appendee.append(self.rate("network.outgoing.bytes"))
                        continue

                try:
                    appendee.append(element.get(key))
                except AttributeError:
                    appendee.append("")

            # print appendee
            self.add_line(appendee)

    def add_line(self, line):
        if not self.closed:
            return self.lines.append(line)
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

        # csvwriter.writerow(self.config["row_layout"])
        for line in self.lines:
            # Line is expected to be an iterable row
            csvwriter.writerow(line)

        # write a blank line
        csvwriter.writerow([])
        # write total
        total = ["total: ", self.total()]
        csvwriter.writerow(total)

        fh.close()
        self.closed = True

    def total(self):
        total = Decimal(0.0)
        for line in self.lines:
            try:
                total += line[len(line) - 1]
            except (TypeError, ValueError):
                total += 0
        return total
