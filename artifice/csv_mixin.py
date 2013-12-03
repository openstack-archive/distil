from csv import writer


class CSV_File_mixin(object):

    def write_output(self):
        try:
            read = open(self.filename)
            raise RuntimeError("Can't write to an existing file!")
        except IOError:
            pass
        fh = open(self.filename, "w")

        csvwriter = writer(fh, dialect='excel', delimiter=',')
        for line in self.lines:
            # Line is expected to be an iterable row
            csvwriter.writerow(line)

        fh.close()
