# Copyright 2017 Catalyst IT Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.


class BaseDriver(object):
    """Base class for ERP drivers.
    """
    conf = None

    def __init__(self, conf):
        self.conf = conf

    def get_products(self, regions=[]):
        """List products based o given regions

        :param regions: List of regions to get projects
        :returns Dict of products based on the given regions
        """
        raise NotImplementedError()

    def create_product(self, product):
        """Create product in Odoo.

        :param product: info used to create product
        """
        raise NotImplementedError()

    def get_credits(self, project_id, expiry_date):
        """Get project credits

        :param project_id: Project ID
        :param expiry_date: 
        :returns list of credits current project can get
        """
        raise NotImplementedError()

    def create_credit(self, project_name, expiry_date, credit,
                      project_id=None):
        """Get project credits

        :param project_id: Project id.
        :param expiry_date: Expiry date of credits.
        :param project_id: Project ID.
        :return: All credits before the expiry date.
        """
        raise NotImplementedError()

    def get_invoices(self, start, end, project_id, detailed=False):
        """Get history invoices from ERP service given a time range.

        :param start: Start time, a datetime object.
        :param end: End time, a datetime object.
        :param project_id: project ID.
        :param detailed: If get detailed information or not.
        :return: The history invoices information for each month.
        """
        raise NotImplementedError()

    def get_quotations(self, region, project_id, measurements=[], resources=[],
                       detailed=False):
        """Get usage cost for current month.

        It depends on ERP system to decide how to get current month cost.

        :param region: Region name.
        :param project_id: Project ID.
        :param measurements: Current month usage.
        :param resources: List of resources.
        :param detailed: If get detailed information or not.
        :return: Current month quotation.
        """

        raise NotImplementedError()
