import unittest
from . import test_interface
from artifice.interface import Artifice
from artifice import database
import os
import glob
import mock
from decimal import *

from sqlalchemy import create_engine

from artifice.models import Session

import csv, yaml

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

try:
    fn = os.path.abspath(__file__)
    path, f = os.path.split(fn)
except NameError:
    path = os.getcwd()


class TestInvoice(test_interface.TestInterface):

    def tearDown(self):

        super(TestInvoice, self).tearDown()

    def test_artifice_start_session(self):
        """Loading and instancing the database module works as expected: """ 
        try:
            db = database.Database(None, self.session)
        except ImportError as e:
            self.fail("Couldn't import: %s" % e)
        return db

    def test_adding_to_db(self):

        self.test_get_usage()

        db = self.test_artifice_start_session()
        db.enter(self.usage.vms, self.start, self.end)
        db.enter(self.usage.objects, self.start, self.end)
        db.enter(self.usage.networks, self.start, self.end)
        db.enter(self.usage.volumes, self.start, self.end)

    def test_get_from_db(self):
        self.test_get_usage()

        db = self.test_artifice_start_session()
        db.enter(self.usage.vms, self.start, self.end)
        db.enter(self.usage.objects, self.start, self.end)
        db.enter(self.usage.networks, self.start, self.end)
        db.enter(self.usage.volumes, self.start, self.end)

        tenants = db.tenants(self.start, self.end)
        
        self.assertEqual(len(tenants), 1)

        for tenant in tenants:
            print tenant.name
            self.assertEqual(tenant.name, "no tenant DB yet")
            for resource in tenant.resources.values():
                print "  " + str(resource.metadata)
                print "  " + resource.id

                if resource.id == "23dd6f29-754f-41a8-b488-6c0113af272b":
                    strat = resource.usage_strategies["m1.tiny"]
                    self.assertEqual(strat.volume, 6)
                if resource.id == "3d736ab0-3429-43bb-86ef-bba41fffd6ef":
                    strat = resource.usage_strategies["m1.medium"]
                    self.assertEqual(strat.volume, 1)
                if resource.id == "3e3da06d-9a0e-4412-984a-c189dde81377":
                    strat = resource.usage_strategies["m1.tiny"]
                    self.assertEqual(strat.volume, 1)
                if resource.id == "388b3939-8854-4a1b-a133-e738f1ffbb0a":
                    strat = resource.usage_strategies["m1.micro"]
                    self.assertEqual(strat.volume, 1)
                if resource.id == "8a78fa56de8846cb89c7cf3f37d251d5":
                    strat = resource.usage_strategies["object_size"]
                    self.assertEqual(strat.volume, 180667.463)
                if (resource.id ==
                        "nova-instance-instance-00000001-fa163e915745"):
                    strat = resource.usage_strategies["outgoing_megabytes"]
                    self.assertEqual(strat.volume, 26.134)
                    strat = resource.usage_strategies["incoming_megabytes"]
                    self.assertEqual(strat.volume, 30.499)
                if (resource.id ==
                        "nova-instance-instance-00000004-fa163e99f87f"):
                    strat = resource.usage_strategies["outgoing_megabytes"]
                    self.assertEqual(strat.volume, 8.355)
                    strat = resource.usage_strategies["incoming_megabytes"]
                    self.assertEqual(strat.volume, 7.275)

                for usage in resource.usage_strategies.values():
                    print "    " + usage.service
                    print "    " + str(usage.volume)


