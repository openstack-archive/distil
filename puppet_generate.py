import sys
# pip install requirements-parser
import requirements

class Requirements(object):

    def __init__(self):
        self.reqs = []

    def parse(self, stream):
        self.reqs = requirements.parse(stream)

    def package_list(self):
        final = """"""
        for req in self.reqs:
            final += """
package {"%(package)s":
    ensure   => "%(version)s",
    provider => pip
}
""" % {"package": req.name, "version": req.specs[0][1] }
        return final

    def requirement_list(self):
        return ",\n".join( [ """Package[%(package)s]""" % 
            {"package": req.name } for req in self.reqs ] )


if __name__ == '__main__':
    import argparse
    a = argparse.ArgumentParser()
    a.add_argument("-f", dest="filename")
    a.add_argument("-l", dest="list_", action="store_true")
    
    args = a.parse_args()

    if args.filename == "-":
        # We're following standardized posix thing
        fh = sys.stdin
    else:
        try:
            fh = open(args.filename)
        except IOError as e:
            print "Couldn't open %s" % args.filename
            sys.exit(1)

    r = Requirements()
    r.parse(fh)
    if args.list_:
        print r.requirement_list()
        sys.exit(0)
    print r.package_list()
