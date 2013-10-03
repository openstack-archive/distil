import os
from csv import writer
from artifice import invoice
import yaml

class Csv(invoice.Invoice):

    def __init__(self, tenant, config):
        self.config = config
        self.tenant = tenant
        self.lines = []
        self.closed = False
        self.start = None
        self.end = None
        # Should the rates information be part of the CSV code,
        # or part of the full run?
        try:
            fh = open(config["rates"][ "file" ])
            self.costs = yaml.load( fh.read() )
            fh.close()
        except IOError:
            # That's problem
            print "couldn't load %s" % config["rates_file"]
            raise
        except KeyError:
            # Couldn't find it!
            print "Missing rates_file in config!"
            raise

    def bill(self, usage):
        # Usage is one of VMs, Storage, or Volumes.
        for element in usage:
            appendee = []
            for key in self.config["row_layout"]:
                if key == "cost":
                    # Ignore costs for now.
                    appendee.append(None)
                    continue
                # What do we expect element to be?
                if key == "type":
                    # Fetch the 'pretty' name from the mappings, if any
                    # The default is that this returns the internal name
                    appendee.append(self.pretty_name(element.get(key)))
                    continue
                try:
                    appendee.append( element.get(key) )
                except AttributeError:
                    appendee.append("")

            try:
                x = self.config["row_layout"].index("cost")
                appendee[ x ] = element.amount.volume() * \
                        self.costs.get( element.type, 0 )

            except ValueError:
                # Not in this array. Well okay.
                # We're not storing cost info, apparently.
                raise RuntimeError("No costing information in CSV layout.")

            # print appendee
            self.add_line(appendee)

    def add_line(self, line):
        if not self.closed:
            return self.lines.append(line)
        raise AttributeError("Can't add to a closed invoice")

    @property
    def filename(self):
        fn = os.path.join(
            self.config["output_path"],
            self.config["output_file"] % dict(tenant=self.tenant,
                start=self.start, end=self.end)
        )
        return fn
    def close(self):
        try:
            read = open( self.filename )
            raise RuntimeError("Can't write to an existing file!")
        except IOError:
            pass
        fh = open(self.filename, "w")

        csvwriter = writer(fh, dialect='excel', delimiter=',')
        for line in self.lines:
            # Line is expected to be an iterable row
            csvwriter.writerow(line)

        fh.close()
        self.closed = True

    def total(self):
        total = 0.0
        for line in self.lines:
            # Cheatery
            # Creates a dict on the fly from the row layout and the line value
            v = dict([(k, v) for k, v in zip(self.config["row_layout"], line)])
            try:
                total += float(v["cost"])
            except (TypeError, ValueError):
                total += 0
        return total
