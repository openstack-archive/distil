import os
from csv import writer

class Csv(object):

    def __init__(self, tenant, config):
        self.config = config
        self.tenant = tenant
        self.lines = []
        self.closed = False
        self.start = None
        self.end = None

    def bill(self, usage):
        # Usage is an ordered list?
        for element in usage:
            appendee = []
            for key in self.config["row_layout"]:
                # What do we expect element to be?
                try:
                    appendee.append( element.get(key) )
                except AttributeError:
                    appendee.append("")
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
            total += v["cost"] or 0
        return total