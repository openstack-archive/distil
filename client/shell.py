# Copyright (C) 2014 Catalyst IT Ltd
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

#!/usr/bin/env python

import os
import json
from client import Client
import exc


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()

    #main args:
    parser.add_argument('-k', '--insecure',
                        default=False,
                        action='store_true',
                        help="Explicitly allow distilclient to "
                        "perform \"insecure\" SSL (https) requests. "
                        "The server's certificate will "
                        "not be verified against any certificate "
                        "authorities. This option should be used with "
                        "caution.")

    parser.add_argument('--os-cacert',
                        metavar='<ca-certificate-file>',
                        dest='os_cacert',
                        help='Path of CA TLS certificate(s) used to verify'
                        'the remote server\'s certificate. Without this '
                        'option distil looks for the default system '
                        'CA certificates.')

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

    parser.add_argument('--os-service-type',
                        help='Defaults to env[OS_SERVICE_TYPE].',
                        default='rating')

    parser.add_argument('--os-endpoint-type',
                        help='Defaults to env[OS_ENDPOINT_TYPE].',
                        default='publicURL')

    parser.add_argument("--distil-url",
                        help="Distil endpoint, defaults to env[DISTIL_URL]",
                        default=os.environ.get('DISTIL_URL'))

    # commands:
    subparsers = parser.add_subparsers(help='commands', dest='command')

    usage_parser = subparsers.add_parser(
        'usage', help=('process usage for all tenants'))

    usage_parser = subparsers.add_parser(
        'last-collected', help=('get last collected time'))

    sales_parser = subparsers.add_parser(
        'sales-order',
        help=('create sales orders for given tenants'))
    sales_parser.add_argument(
        "-t", "--tenant", dest="tenants",
        help='Tenants to create sales orders for.',
        action="append", default=[],
        required=True)
    sales_parser.add_argument(
        "-e", "--end", dest="end",
        help='end date for sales order.')

    draft_parser = subparsers.add_parser(
        'sales-draft',
        help=('create sales drafts for given tenants'))
    draft_parser.add_argument(
        "-t", "--tenant", dest="tenants",
        help='Tenants to create sales drafts for.',
        action="append", required=True)
    draft_parser.add_argument(
        "-e", "--end", dest="end",
        help='end date for sales order.')

    historic_parser = subparsers.add_parser(
        'sales-historic',
        help=('regenerate historic sales orders for given tenants,' +
              'at given date'))
    historic_parser.add_argument(
        "-t", "--tenant", dest="tenants",
        help='Tenants to create sales drafts for.',
        action="append", required=True)
    historic_parser.add_argument(
        "-d", "--date", dest="date",
        help='target search date for sales order.',
        required=True)

    range_parser = subparsers.add_parser(
        'sales-range',
        help=('regenerate historic sales orders for given tenants,' +
              'in a given range'))
    range_parser.add_argument(
        "-t", "--tenant", dest="tenants",
        help='Tenants to create sales drafts for.',
        action="append", required=True)
    range_parser.add_argument(
        "-s", "--start", dest="start",
        help='start of range for sales orders.',
        required=True)
    range_parser.add_argument(
        "-e", "--end", dest="end",
        help='end of range for sales orders. Defaults to now.',
        default=None)

    args = parser.parse_args()

    if not (args.os_auth_token and args.distil_url):
        if not args.os_username:
            raise exc.CommandError("You must provide a username via "
                                   "either --os-username or via "
                                   "env[OS_USERNAME]")

        if not args.os_password:
            raise exc.CommandError("You must provide a password via "
                                   "either --os-password or via "
                                   "env[OS_PASSWORD]")

        if not (args.os_tenant_id or args.os_tenant_name):
            raise exc.CommandError("You must provide a tenant_id via "
                                   "either --os-tenant-id or via "
                                   "env[OS_TENANT_ID]")

        if not args.os_auth_url:
            raise exc.CommandError("You must provide an auth url via "
                                   "either --os-auth-url or via "
                                   "env[OS_AUTH_URL]")

    kwargs = vars(args)

    client = Client(**kwargs)

    if args.command == 'usage':
        response = client.usage()
        print json.dumps(response, indent=2)

    if args.command == 'last-collected':
        response = client.last_collected()
        print json.dumps(response, indent=2)

    if args.command == 'sales-order':
        response = client.sales_order(args.tenants, args.end, False)
        print json.dumps(response, indent=2)

    if args.command == 'sales-draft':
        response = client.sales_order(args.tenants, args.end, True)
        print json.dumps(response, indent=2)

    if args.command == 'sales-historic':
        response = client.sales_historic(args.tenants, args.date)
        print json.dumps(response, indent=2)

    if args.command == 'sales-range':
        response = client.sales_range(args.tenants, args.start, args.end)
        print json.dumps(response, indent=2)
