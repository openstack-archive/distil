#!/usr/bin/env python

import os
from client import Client

# import yaml

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()

    #main args:
    parser.add_argument('--os-username',
                        default=os.environ.get('OS_USERNAME'),
                        help='Defaults to env[OS_USERNAME]')

    parser.add_argument('--os-password',
                        default=os.environ.get('OS_PASSWORD'),
                        help='Defaults to env[OS_PASSWORD]')

    parser.add_argument('--os-tenant-id',
                        default=os.environ.get('OS_TENANT_ID'),
                        help='Defaults to env[OS_TENANT_ID]')

    parser.add_argument('--os-tenant-name',
                        default=os.environ.get('OS_TENANT_NAME'),
                        help='Defaults to env[OS_TENANT_NAME]')

    parser.add_argument('--os-auth-url',
                        default=os.environ.get('OS_AUTH_URL'),
                        help='Defaults to env[OS_AUTH_URL]')

    parser.add_argument('--os-region-name',
                        default=os.environ.get('OS_REGION_NAME'),
                        help='Defaults to env[OS_REGION_NAME]')

    parser.add_argument('--os-auth-token',
                        default=os.environ.get('OS_AUTH_TOKEN'),
                        help='Defaults to env[OS_AUTH_TOKEN]')

    parser.add_argument("-c", "--config", dest="config",
                        help="Config file",
                        default="/etc/artifice/conf.yaml")

    # commands:
    subparsers = parser.add_subparsers(help='commands', dest='command')

    usage_parser = subparsers.add_parser('usage', help=('process usage' +
                                                        ' for all tenants'))

    sales_parser = subparsers.add_parser('sales-order',
                                         help=('create sales orders for '
                                               'given tenants'))
    sales_parser.add_argument(
        "-t", "--tenant", dest="tenants",
        help='Tenants to create sales orders for.',
        action="append", default=[])

    draft_parser = subparsers.add_parser('sales-draft',
                                         help=('create sales drafts for '
                                               'given tenants'))
    draft_parser.add_argument(
        "-t", "--tenant", dest="tenants",
        help='Tenants to create sales drafts for.',
        action="append", default=[])

    args = parser.parse_args()

    conf = {'api': {'endpoint': 'http://0.0.0.0:8000/',
                    'token': 'sah324sdf5wad4dh839uhjuUH'}}

    # try:
    #     conf = yaml.load(open(args.config).read())
    # except IOError:
    #     print "couldn't load %s " % args.config
    #     sys.exit(1)

    client = Client(conf["api"]["endpoint"],
                    token=conf["api"]["token"])

    if args.command == 'usage':
        client.usage()

    if args.command == 'sales-order':
        client.sales_order(args.tenants, False)

    if args.command == 'sales-draft':
        client.sales_order(args.tenants, True)
