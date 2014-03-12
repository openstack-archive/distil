from webtest import TestApp
import unittest

@unittest.skip
class TestKeystone(unittest.TestCase):
    """Requires a running environment and a running Keystone that
    we can perform requests against.

    Currently disabled.
    """

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_invalid_credentials(self):
        """Assertion that invalid credentials raise a 401"""
        pass

    def test_valid_credentials(self):
        """Assertion that valid credentials respond as expected"""
        pass
