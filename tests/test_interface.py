import unittest
from distil.models import Tenant as tenant_model
from distil.models import UsageEntry, Resource, SalesOrder
from sqlalchemy.pool import NullPool

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from datetime import datetime, timedelta

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

from . import PG_DATABASE_URI
from .data_samples import RESOURCES


class TestInterface(unittest.TestCase):

    def setUp(self):

        engine = create_engine(PG_DATABASE_URI, poolclass=NullPool)
        Session = sessionmaker(bind=engine)
        self.session = Session()
        self.objects = []
        self.session.rollback()
        self.called_replacement_resources = False

        self.resources = (RESOURCES["networks"] + RESOURCES["vms"] +
                          RESOURCES["objects"] + RESOURCES["volumes"] +
                          RESOURCES["ips"])

        # TODO: make these constants.
        self.end = datetime.utcnow()
        self.start = self.end - timedelta(days=30)

    def tearDown(self):

        self.session.query(UsageEntry).delete()
        self.session.query(Resource).delete()
        self.session.query(SalesOrder).delete()
        self.session.query(tenant_model).delete()
        self.session.commit()
        self.session.close()
        self.contents = None
        self.resources = []
