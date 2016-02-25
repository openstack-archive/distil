#!/usr/bin/env python2
import sys
import os
import pprint
import argparse
import math
import ConfigParser
from decimal import Decimal

import odoorpc

# requires distilclient>=0.5.1
from distilclient.client import Client as DistilClient


parser = argparse.ArgumentParser()
parser.add_argument('--start', required=True, help='Start date')
parser.add_argument('--end', required=True, help='End date')

args = parser.parse_args()

conf = ConfigParser.ConfigParser()
conf.read(['glue.ini'])

region = conf.get('openstack', 'region')

oerp = odoorpc.ODOO(
    conf.get('odoo', 'hostname'),
    protocol=conf.get('odoo', 'protocol'),
    port=conf.getint('odoo', 'port'),
    version=conf.get('odoo', 'version')
)
oerp.login(
    conf.get('odoo', 'database'),
    conf.get('odoo', 'user'),
    conf.get('odoo', 'password')
)

# debug helper
def dump_all(model, fields, conds=None):
    print '%s:' % model
    ids = oerp.search(model, conds or [])
    objs = oerp.read(model, ids)
    for obj in objs:
        print ' %s %s' % (obj['id'], {f:obj[f] for f in fields})

pricelist_model = oerp.env['product.pricelist']
pricelist = oerp.search('product.pricelist',
                        [('name', '=', conf.get('odoo', 'export_pricelist'))])

product_category = oerp.search('product.category',
                               [('name', '=', conf.get('odoo', 'product_category'))])

product_ids = oerp.search('product.product',
                          [('categ_id', '=', product_category[0]),
                           ('sale_ok', '=', True),
                           ('active', '=', True)])

products = oerp.read('product.product', product_ids)

prices = {}

for p in products:
    if not p['name_template'].startswith(region + '.'):
        continue
    base_name = p['name_template'][len(region)+1:]
    # exported prices are for one unit -- do not take into account
    # any bulk pricing rules.
    unit_price = pricelist_model.price_get([pricelist[0]], p['id'], 1)[str(pricelist[0])]
    prices[base_name] = unit_price
    print '%s %s' % (base_name, unit_price)

# create the snapshot in distil
dc = DistilClient(
    os_username=os.getenv('OS_USERNAME'),
    os_password=os.getenv('OS_PASSWORD'),
    os_tenant_id=os.getenv('OS_TENANT_ID'),
    os_auth_url=os.getenv('OS_AUTH_URL'),
    os_region_name=os.getenv('OS_REGION_NAME'))

dc.set_prices(args.start, args.end, prices)
