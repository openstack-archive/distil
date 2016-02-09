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
        'collect-usage', help=('process usage for all tenants'))

    last_collected_parser = subparsers.add_parser(
        'last-collected', help=('get last collected time'))

    get_usage_parser = subparsers.add_parser(
        'get-usage', help=('get raw aggregated usage'))

    get_usage_parser.add_argument(
        "-t", "--tenant", dest="tenant",
        help='Tenant to get usage for',
        required=True)

    get_usage_parser.add_argument(
        "-s", "--start", dest="start",
        help="Start time",
        required=True)

    get_usage_parser.add_argument(
        "-e", "--end", dest="end",
        help="End time",
        required=True)

    get_rated_parser = subparsers.add_parser(
        'get-rated', help=('get rated usage'))

    get_rated_parser.add_argument(
        "-t", "--tenant", dest="tenant",
        help='Tenant to get usage for',
        required=True)

    get_rated_parser.add_argument(
        "-s", "--start", dest="start",
        help="Start time",
        required=True)

    get_rated_parser.add_argument(
        "-e", "--end", dest="end",
        help="End time")

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

    client = Client(kwargs.get('distil_url', None),
                    kwargs.get('os_auth_token', None),
                    kwargs.get('os_username', None),
                    kwargs.get('os_password', None),
                    kwargs.get('os_tenant_id', None),
                    kwargs.get('os_tenant_name', None),
                    kwargs.get('os_auth_url', None),
                    kwargs.get('os_region_name', None),
                    kwargs.get('os_cacert', None),
                    kwargs.get('insecure', None),
                    kwargs.get('os_service_type', None),
                    kwargs.get('os_endpoint_type', None))

    if args.command == 'collect-usage':
        response = client.collect_usage()
        print json.dumps(response, indent=2)

    if args.command == 'last-collected':
        response = client.last_collected()
        print json.dumps(response, indent=2)

    if args.command == 'get-usage':
        response = client.get_usage(args.tenant, args.start, args.end)
        print json.dumps(response, indent=2)

    if args.command == 'get-rated':
        response = client.get_rated(args.tenant, args.start, args.end)
        print json.dumps(response, indent=2)
