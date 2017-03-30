# Copyright (C) 2017 Catalyst IT Ltd
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
import os

import mock

from distil.collector import base as collector_base
from distil.tests.unit import base


class CollectorBaseTest(base.DistilWithDbTestCase):
    def setUp(self):
        super(CollectorBaseTest, self).setUp()

        meter_mapping_file = os.path.join(
            os.environ["DISTIL_TESTS_CONFIGS_DIR"],
            'meter_mappings.yaml'
        )
        self.conf.set_default(
            'meter_mappings_file',
            meter_mapping_file,
            group='collector'
        )

        transformer_file = os.path.join(
            os.environ["DISTIL_TESTS_CONFIGS_DIR"],
            'transformer.yaml'
        )
        self.conf.set_default(
            'transformer_file',
            transformer_file,
            group='collector'
        )

    @mock.patch('distil.common.openstack.get_root_volume')
    @mock.patch('distil.common.openstack.get_image')
    def test_get_os_distro_instance_active_boot_from_image(self,
                                                           mock_get_image,
                                                           mock_get_root):
        mock_get_root.return_value = None
        mock_get_image.return_value = {'os_distro': 'linux'}

        entry = {
            'resource_id': 'fake_vm_id',
            'metadata': {
                'image_ref_url': 'http://cloud:9292/images/1-2-3-4'
            }
        }

        collector = collector_base.BaseCollector()
        os_distro = collector._get_os_distro(entry)

        mock_get_image.assert_called_once_with('1-2-3-4')

        self.assertEqual('linux', os_distro)

    @mock.patch('distil.common.openstack.get_root_volume',
                side_effect=Exception())
    @mock.patch('distil.common.openstack.get_image')
    def test_get_os_distro_instance_delete_boot_from_image(self,
                                                           mock_get_image,
                                                           mock_get_root):
        mock_get_root.return_value = None
        mock_get_image.return_value = {'os_distro': 'linux'}

        entry = {
            'resource_id': 'fake_vm_id',
            'metadata': {
                'image_ref_url': 'http://cloud:9292/images/1-2-3-4'
            }
        }

        collector = collector_base.BaseCollector()
        os_distro = collector._get_os_distro(entry)

        mock_get_image.assert_called_once_with('1-2-3-4')

        self.assertEqual('linux', os_distro)

    @mock.patch('distil.common.openstack.get_root_volume')
    def test_get_os_distro_instance_active_boot_from_volume(self,
                                                            mock_get_root):
        class Volume(object):
            def __init__(self):
                self.volume_image_metadata = {'os_distro': 'linux'}

        mock_get_root.return_value = Volume()

        entry = {
            'resource_id': 'fake_vm_id',
            'metadata': {
                'image_ref_url': None
            }
        }

        collector = collector_base.BaseCollector()
        os_distro = collector._get_os_distro(entry)

        mock_get_root.assert_called_once_with('fake_vm_id')

        self.assertEqual('linux', os_distro)

    @mock.patch('distil.common.openstack.get_root_volume',
                side_effect=Exception())
    def test_get_os_distro_instance_delete_boot_from_volume(self,
                                                            mock_get_root):
        entry = {
            'resource_id': 'fake_vm_id',
            'metadata': {
                'image_ref_url': None
            }
        }

        collector = collector_base.BaseCollector()
        os_distro = collector._get_os_distro(entry)

        self.assertEqual('unknown', os_distro)
