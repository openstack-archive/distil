#!/usr/bin/python
from distil.api import web
import yaml
import sys

import argparse
a = argparse.ArgumentParser("Web service for Distil")

a.add_argument("-c", "--config", dest="config", help="Path to config file", default="/etc/distil/conf.yaml")
a.add_argument("-i", "--interface", dest="ip", help="IP address to serve on.", default="0.0.0.0")
a.add_argument("-p", "--port", help="port to serve on", default="8000")

args = a.parse_args()

conf = None

try:
    with open(args.config) as f:
        conf = yaml.load(f)
except IOError as e:
    print "Couldn't load config file: %s" % e
    sys.exit(1)


app = web.get_app(conf)
app.run(host=args.ip, port=int(args.port))
