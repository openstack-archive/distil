#!/usr/bin/env python

from artifice import interface
import datetime

date_format = "%Y-%m-%dT%H:%M:%S"
other_date_format = "%Y-%m-%dT%H:%M:%S.%f"

date_fmt_fnc = lambda x: datetime.datetime.strptime(date_fmt)

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

    parser.add_argument("--from", dest="start", help="When to start our range, date format %s", type=date_fmt_fnc)
    parser.add_argument("--to", dest="end", help="When to end our date range. Defaults to yesterday.",
        type=date_fmt_fnc, default=datetime.datetime.now() - datetime.timedelta(days=1) )

    parser.add_argument("--config", dest="config", help="Config file", default="/etc/niceometer/conf.yaml")

    args = parser.parse_args()

    # Make ourselves a nice interaction object
    n = niceometer.Niceometer(conf["username"], conf["password"], conf["admin_tenant"])
    tenants = args.tenants
    if not args.tenants:
        # only parse this list of tenants
        tenants = n.tenants

    for tenant_name in tenants:
        # artifact = n.tenant(tenant_name).section(section).usage(args.start, args.end)
        # data should now be an artifact-like construct.
        # Data also knows about Samples, where as an Artifact doesn't.

        # An artifact knows its section
        tenant = n.tenant(tenant_name)
        # Makes a new invoice up for this tenant.
        invoice = tenant.invoice(args.start, args.end)
        print "Tenant: %s" % tenant.name
        print "Range: %s -> %s" % (args.start, args.end)

        # usage = tenant.usage(start, end)
        usage = tenant.usage(args.start, args.end)
        # A Usage set is the entirety of time for this Tenant.
        # It's not time-limited at all.
        # But the
        usage.save()
        invoice.bill(usage.vms)
        invoice.bill(usage.volumes)
        invoice.bill(usage.objects)
        invoice.close()

        print invoice.total()

        # for datacenter, sections in usage.iteritems():
        #     # DC is the name of the DC/region. Or the internal code. W/E.
        #     print datacenter

        #     for section_name in args.sections:
        #         assert section in sections

        #         # section = sections[ section ]
        #         print sections[section_name]
        #         for resources in sections[section_name]:
        #             for resource in resources:
        #                 print resource
        #                 for meter in resource.meters:
        #                     usage = meter.usage(start, end)
        #                     if usage.has_been_saved():
        #                         continue
        #                     print usage.volume()
        #                     print usage.cost()
        #                     usage.save()
        #                     # Finally, bill it.
        #                     # All of these things need to be converted to the
        #                     # publicly-viewable version now.
        #                     invoice.bill(datacenter, resource, meter, usage)

        #         # Section is going to be in the set of vm, network, storage, image
        #         # # or just all of them.
        #         # # It's not going to be an individual meter name.
        #         # artifacts = section.usage(args.start, args.end)
        #         # for artifact in artifacts:
        #         #     if artifact.has_been_saved:
        #         #         # Does this artifact exist in the DB?
        #         #         continue
        #         #     artifact.save() # Save to the Artifact storage
        #         #     # Saves to the invoice.
        #         #     invoice.bill ( artifact )
        #         #     # artifact.bill( invoice.id )
        #         # print "%s: %s" % (section.name, artifact.volume)
