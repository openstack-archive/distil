# Copyright 2016 Catalyst IT Ltd
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

import abc
from datetime import timedelta
import re
import yaml

from oslo_config import cfg
from oslo_log import log as logging

from distil.db import api as db_api
from distil import exceptions as exc
from distil import transformer as d_transformer
from distil.common import constants
from distil.common import general
from distil.common import openstack

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class BaseCollector(object):
    def __init__(self):
        meter_file = CONF.collector.meter_mappings_file

        with open(meter_file, 'r') as f:
            try:
                self.meter_mappings = yaml.load(f)
            except yaml.YAMLError:
                raise exc.InvalidConfig("Invalid yaml file: %s" % meter_file)

    @abc.abstractmethod
    def get_meter(self, project, meter, start, end):
        raise NotImplementedError

    def collect_usage(self, project, start, end):
        LOG.info('collect_usage by %s for project: %s(%s)' %
                 (self.__class__.__name__, project['id'], project['name']))

        windows = list(general.generate_windows(start, end))

        if CONF.collector.max_windows_per_cycle > 0:
            windows = windows[:CONF.collector.max_windows_per_cycle]

        if not windows:
            LOG.info("Skipped project %s(%s), less than 1 hour since last "
                     "collection time.", project['id'], project['name'])

        for window_start, window_end in windows:
            LOG.info("Project %s(%s) slice %s %s", project['id'],
                     project['name'], window_start, window_end)

            resources = {}
            usage_entries = []
            # Set 10min as leadin time when getting samples.
            actual_start = window_start - timedelta(minutes=10)

            try:
                for mapping in self.meter_mappings:
                    # Invoke get_meter function of specific collector.
                    usage = self.get_meter(project['id'], mapping['meter'],
                                           actual_start, window_end)

                    usage_by_resource = {}
                    self._filter_and_group(usage, usage_by_resource)
                    self._transform_usages(project['id'], usage_by_resource,
                                           mapping, window_start, window_end,
                                           resources, usage_entries)

                # Insert resources and usage_entries, and update last collected
                # time of project within one session.
                db_api.usages_add(project['id'], resources, usage_entries,
                                  window_end)
                LOG.info('Finish project %s(%s) slice %s %s', project['id'],
                         project['name'], window_start, window_end)
            except Exception as e:
                LOG.exception(
                    "IntegrityError for %s(%s) in window: %s - %s, reason: %s",
                    project['id'], project['name'],
                    window_start.strftime(constants.iso_time),
                    window_end.strftime(constants.iso_time),
                    str(e)
                )
                return

    def _filter_and_group(self, usage, usage_by_resource):
        trust_sources = set(CONF.collector.trust_sources)
        for u in usage:
            # if we have a list of trust sources configured, then
            # discard everything not matching.
            # NOTE(flwang): When posting samples by ceilometer REST API, it
            # will use the format <tenant_id>:<source_name_from_user>
            # so we need to use a regex to recognize it.
            if (trust_sources and
                    all([not re.match(source, u['source'])
                         for source in trust_sources])):
                LOG.warning('Ignoring untrusted usage sample from source `%s`',
                            u['source'])
                continue

            resource_id = u['resource_id']
            entries = usage_by_resource.setdefault(resource_id, [])
            entries.append(u)

    def _get_os_distro(self, entry):
        os_distro = 'unknown'

        try:
            # Check if the VM is booted from volume first. When VM is booted
            # from a windows image and do a rebuild using a linux image, the
            # 'image_ref' property will be set inappropriately.
            root_vol = openstack.get_root_volume(entry['resource_id'])

            if root_vol:
                image_meta = getattr(root_vol, 'volume_image_metadata', {})
                os_distro = image_meta.get('os_distro', 'unknown')
            else:
                # Boot from image
                image_id = entry['metadata'].get('image.id', None)
                image_id = image_id or entry['metadata'].get('image_ref', None)

                os_distro = getattr(
                    openstack.get_image(image_id),
                    'os_distro',
                    'unknown'
                )
        except Exception as e:
            LOG.warning(
                'Error occured when getting os_distro, reason: %s', str(e)
            )

        return os_distro

    def _get_resource_info(self, project_id, resource_id, resource_type, entry,
                           defined_meta):
        resource_info = {'type': resource_type}

        for field, parameters in defined_meta.items():
            for source in parameters['sources']:
                try:
                    value = entry['metadata'][source]
                    resource_info[field] = (
                        parameters['template'] % value
                        if 'template' in parameters else value
                    )
                    break
                except KeyError:
                    # Just means we haven't found the right value yet.
                    # Or value isn't present.
                    pass

        # If the resource is already created, don't update properties below.
        if not db_api.resource_get_by_ids(project_id, [resource_id]):
            if resource_type == 'Virtual Machine':
                resource_info['os_distro'] = self._get_os_distro(entry)
            if resource_type == 'Object Storage Container':
                # NOTE(flwang): It's safe to get container name by /, since
                # Swift doesn't allow container name with /.
                idx = resource_id.index('/') + 1
                resource_info['name'] = resource_id[idx:]

        return resource_info

    def _transform_usages(self, project_id, usage_by_resource, mapping,
                          window_start, window_end, resources, usage_entries):
        service = (mapping['service'] if 'service' in mapping
                   else mapping['meter'])

        transformer = d_transformer.get_transformer(mapping['transformer'])

        for res_id, entries in usage_by_resource.items():
            transformed = transformer.transform_usage(
                service, entries, window_start, window_end
            )

            LOG.debug(
                'After transformation, usage for resource %s: %s' %
                (res_id, transformed)
            )

            if transformed:
                res_id = mapping.get('res_id_template', '%s') % res_id
                res_info = self._get_resource_info(
                    project_id,
                    res_id,
                    mapping['type'],
                    entries[-1],
                    mapping['metadata']
                )

                res = resources.setdefault(res_id, res_info)
                res.update(res_info)

                for service, volume in transformed.items():
                    entry = {
                        'service': service,
                        'volume': volume,
                        'unit': mapping['unit'],
                        'resource_id': res_id,
                        'start': window_start,
                        'end': window_end,
                        'tenant_id': project_id
                    }
                    usage_entries.append(entry)
