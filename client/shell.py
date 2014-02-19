#!/usr/bin/env python

# import sys
from client import Client

# import yaml

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(help='commands', dest='command')

    parser.add_argument(
        "-c", "--config", dest="config",
        help="Config file",
        default="/etc/artifice/conf.yaml")

    usage_parser = subparsers.add_parser('usage', help=('process usage' +
                                                        ' for given tenants'))
    usage_parser.add_argument(
        "-t", "--tenant", dest="tenants",
        help='Tenants to process usage for.',
        action="append", default=[])

    sales_parser = subparsers.add_parser('sales-order',
                                         help=('create sales orders for '
                                               'given tenants'))
    sales_parser.add_argument(
        "-t", "--tenant", dest="tenants",
        help='Tenants to create sales orders for.',
        action="append", default=[])

    args = parser.parse_args()

    conf = {'api': {'endpoint': 'http://0.0.0.0/',
                    'token': 'sah324sdf5wad4dh839uhjuUH'}}

    # try:
    #     conf = yaml.load(open(args.config).read())
    # except IOError:
    #     print "couldn't load %s " % args.config
    #     sys.exit(1)

    client = Client(conf["api"]["endpoint"],
                    token=conf["api"]["token"])

    if args.command == 'usage':
        client.usage(args.tenants)

    if args.command == 'sales-order':
        client.sales_order(args.tenants)
