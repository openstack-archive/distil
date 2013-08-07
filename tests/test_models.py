import unittest
from artifice.models import usage, tenants, resources, Session


class TestTenant(unittest.TestCase):
    def test_create_tenant(self):

        pass

    def test_create_identical_tenant_fails(self):

        pass



class TestResource(unittest.TestCase):


    def test_create_resource(self):
        pass

    def test_create_resource_with_bad_tenant(self):
        pass

    def test_create_resource_without_tenant(self):
        pass



class TestUsage(unittest.TestCase):

    """Tests various states of the Usage objects."""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_save_to_database(self):
        pass

    def test_overlap_throws_exception(self):
        pass

    def test_non_overlap_does_not_throw_exception(self):
        pass

    def test_tenant_does_not_exist(self):
        pass

    def test_resource_does_not_exist(self):
        pass