#!/usr/bin/env python

import os, sys

try:
    from artifice import interface
except ImportError:
    loc, fn = os.path.split(__file__)
    print loc
    here =  os.path.abspath(os.path.join(loc +"/../"))
    sys.path.insert(0, here)
    # # Are we potentially in a virtualenv? Add that in.
    # if os.path.exists( os.path.join(here, "lib/python2.7" ) ):
    #     sys.path.insert(1, os.path.join(here, "lib/python2.7"))
    from artifice import interface

import datetime
import yaml

date_format = "%Y-%m-%dT%H:%M:%S"
other_date_format = "%Y-%m-%dT%H:%M:%S.%f"
date_fmt = "%Y-%m-%d"

def date_fmt_fnc(val):
    return datetime.datetime.strptime(val, date_fmt)

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    # Takes names to display.
    # none means display them all.
    parser.add_argument("-t", "--tenant", dest="tenants", help='Tenant to display', action="append", default=[])

    # Add some sections to show data from.
    # Empty is display all
    parser.add_argument("-s", "--section", dest="sections", help="Sections to display", action="append")


    # Ranging
    # We want to get stuff from, to.

    parser.add_argument(
        "--from",
        dest="start",
        help="When to start our range, date format %s",
        type=date_fmt_fnc,
        default=datetime.datetime.now() - datetime.timedelta(days=31)
    )
    parser.add_argument("--to", dest="end", help="When to end our date range. Defaults to yesterday.",
        type=date_fmt_fnc, default=datetime.datetime.now() - datetime.timedelta(days=1) )

    parser.add_argument("-c", "--config", dest="config", help="Config file", default="/opt/stack/artifice/etc/artifice/conf.yaml")

    args = parser.parse_args()
    print "Range: %s -> %s" % (args.start, args.end)
    try:
        conf = yaml.load(open(args.config).read())
    except IOError:
        # Whoops
        print "couldn't load %s " % args.config
        sys.exit(1)

    # Make ourselves a nice interaction object
    instance = interface.Artifice(conf)
    tenants = args.tenants
    if not args.tenants:
        # only parse this list of tenants
        tenants = instance.tenants

    for tenant_name in tenants:
        # artifact = n.tenant(tenant_name).section(section).usage(args.start, args.end)
        # data should now be an artifact-like construct.
        # Data also knows about Samples, where as an Artifact doesn't.

        # An artifact knows its section
        tenant = instance.tenant(tenant_name)
        # Makes a new invoice up for this tenant.
        invoice = tenant.invoice(args.start, args.end)
        print "Tenant: %s" % tenant.name


        # usage = tenant.usage(start, end)
        usage = tenant.usage(args.start, args.end)
        # A Usage set is the entirety of time for this Tenant.
        # It's not time-limited at all.

        invoice.bill(usage.vms)
        invoice.bill(usage.volumes)
        invoice.bill(usage.objects)

        print invoice.total()