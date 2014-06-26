from setuptools import setup

setup(name='openstack-distil',
      version='0.1',
      description='Distil, a set of APIs for creating billable items from Openstack-Ceilometer',
      author='Aurynn Shaw',
      author_email='aurynn@catalyst.net.nz',
      contributors=["Chris Forbes", "Adrian Turjak"],
      contributor_emails=["chris.forbes@catalyst.net.nz", "adriant@catalyst.net.nz"],
      url='https://github.com/catalyst/distil',
      packages=["distil", "distil.api", "distil.models"]
     )
