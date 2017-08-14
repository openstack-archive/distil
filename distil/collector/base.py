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
import hashlib
import re
import yaml

from oslo_config import cfg
from oslo_log import log as logging

from distil.db import api as db_api
from distil import exceptions as exc
from distil import transformer as d_transformer
from distil.common import constants
from distil.common import openstack

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class BaseCollector(object):
    def __init__(self):
        meter_file = CONF.collector.meter_mappings_file

        with open(meter_file, 'r') as f:
            try:
                self.meter_mappings = yaml.safe_load(f)
            except yaml.YAMLError:
                raise exc.InvalidConfig("Invalid yaml file: %s" % meter_file)

    @abc.abstractmethod
    def get_meter(self, project, meter, start, end):
        raise NotImplementedError

    def collect_usage(self, project, windows):
        """Collect usage for specific tenant.

        :return: True if no error happened otherwise return False.
        """
        LOG.info('collect_usage by %s for project: %s(%s)' %
                 (self.__class__.__name__, project['id'], project['name']))

        for window_start, window_end in windows:
            LOG.info("Project %s(%s) slice %s %s", project['id'],
                     project['name'], window_start, window_end)

            resources = {}
            usage_entries = []

            # NOTE(kong): Set 10min as leadin time when getting samples, this
            # helps us to get correct instance uptime, in case the instance
            # status in first sample is not in our tracked status list.
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
                    "Collection failed for %s(%s) in window: %s - %s, reason: "
                    "%s", project['id'], project['name'],
                    window_start.strftime(constants.iso_time),
                    window_end.strftime(constants.iso_time),
                    str(e)
                )
                return False

        return True

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
        """Gets os distro info for instance.

        1. If instance is booted from image, get distro info from image_ref_url
           in sample's metadata.
        2. If instance is booted from volume, get distro info from
           volume_image_metadata property of the root volume.
        3. If instance is booted from volume and it's already been deleted,
           use default value('unknown').
        """
        os_distro = 'unknown'
        root_vol = None

        try:
            # Check if the VM is booted from volume first. When VM is booted
            # from a windows image and do a rebuild using a linux image, the
            # 'image_ref' property will be set inappropriately.
            root_vol = openstack.get_root_volume(entry['resource_id'])
        except Exception as e:
            LOG.warning(
                'Error occurred when getting root_volume for %s, reason: %s' %
                (entry['resource_id'], str(e))
            )

        if root_vol:
            image_meta = getattr(root_vol, 'volume_image_metadata', {})
            os_distro = image_meta.get('os_distro', 'unknown')
        else:
            # 'image_ref_url' is always there no matter it is sample created by
            # Ceilometer pollster or sent by notification. For instance booted
            # from volume the value is string 'None' in Ceilometer client
            # response.
            image_url = entry['metadata']['image_ref_url']

            if image_url and image_url != 'None':
                image_id = image_url.split('/')[-1]

                try:
                    os_distro = getattr(
                        openstack.get_image(image_id),
                        'os_distro',
                        'unknown'
                    )
                except Exception as e:
                    LOG.warning(
                        'Error occurred when getting image %s, reason: %s' %
                        (image_id, str(e))
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
                # NOTE(flwang): Instead of using the resource_id from the
                # input parameters, here we use the original resource id from
                # the entry. Because the resource_id has been hashed(MD5) to
                # avoid too long.
                idx = entry['resource_id'].index('/') + 1
                resource_info['name'] = entry['resource_id'][idx:]

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

            if transformed:
                res_id = mapping.get('res_id_template', '%s') % res_id

                # NOTE(flwang): Currently the column size of resource id in DB
                # is 100 chars, but the container name of swift could be 256,
                # plus project id and a '/', the id for a swift container
                # could be 32+1+256. So this is a fix for the problem. But
                # instead of checking the length of resource id, here I'm
                # hashing the name only for swift to get a consistent
                # id for swift billing. Another change will be proposed to
                # openstack-billing to handle this case as well.
                if 'o1.standard' in transformed:
                    res_id = hashlib.md5(res_id.encode('utf-8')).hexdigest()

                LOG.debug(
                    'After transformation, usage for resource %s: %s' %
                    (res_id, transformed)
                )

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
