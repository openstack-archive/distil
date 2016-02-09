# Copyright (C) 2014 Catalyst IT Ltd
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

import constants
import helpers
import config
import logging as log
from distil.constants import iso_time, iso_date


class Transformer(object):
    def transform_usage(self, name, data, start, end):
        return self._transform_usage(name, data, start, end)

    def _transform_usage(self, name, data, start, end):
        raise NotImplementedError


class Uptime(Transformer):
    """
    Transformer to calculate uptime based on states,
    which is broken apart into flavor at point in time.
    This is a soon to be deprecated version that uses our state
    metric.
    """

    def _transform_usage(self, name, data, start, end):
        # get tracked states from config
        tracked = config.transformers['uptime']['tracked_states']

        tracked_states = {constants.states[i] for i in tracked}

        usage_dict = {}

        def sort_and_clip_end(usage):
            cleaned = (self._clean_entry(s) for s in usage)
            clipped = [s for s in cleaned if s['timestamp'] < end]
            return clipped

        state = sort_and_clip_end(data)

        if not len(state):
            # there was no data for this period.
            return usage_dict

        last_state = state[0]
        if last_state['timestamp'] >= start:
            last_timestamp = last_state['timestamp']
            seen_sample_in_window = True
        else:
            last_timestamp = start
            seen_sample_in_window = False

        def _add_usage(diff):
            flav = last_state['flavor']
            usage_dict[flav] = usage_dict.get(flav, 0) + diff.total_seconds()

        for val in state[1:]:
            if last_state["counter_volume"] in tracked_states:
                diff = val["timestamp"] - last_timestamp
                if val['timestamp'] > last_timestamp:
                    # if diff < 0 then we were looking back before the start
                    # of the window.
                    _add_usage(diff)
                    last_timestamp = val['timestamp']
                    seen_sample_in_window = True

            last_state = val

        # extend the last state we know about, to the end of the window,
        # if we saw any actual uptime.
        if (end and last_state['counter_volume'] in tracked_states
                and seen_sample_in_window):
            diff = end - last_timestamp
            _add_usage(diff)

        # map the flavors to names on the way out
        return {helpers.flavor_name(f): v for f, v in usage_dict.items()}

    def _clean_entry(self, entry):
        result = {
            'counter_volume': entry['counter_volume'],
            'flavor': entry['resource_metadata'].get(
                'flavor.id', entry['resource_metadata'].get(
                    'instance_flavor_id', 0
                )
            ),
            'timestamp': entry['timestamp']
        }
        return result


class InstanceUptime(Transformer):
    """
    Transformer to calculate uptime based on states,
    which is broken apart into flavor at point in time.
    """

    def _transform_usage(self, name, data, start, end):
        # get tracked states from config
        tracked = config.transformers['uptime']['tracked_states']

        usage_dict = {}

        def sort_and_clip_end(usage):
            cleaned = (self._clean_entry(s) for s in usage)
            clipped = [s for s in cleaned if s['timestamp'] < end]
            return clipped

        state = sort_and_clip_end(data)

        if not len(state):
            # there was no data for this period.
            return usage_dict

        last_state = state[0]
        if last_state['timestamp'] >= start:
            last_timestamp = last_state['timestamp']
            seen_sample_in_window = True
        else:
            last_timestamp = start
            seen_sample_in_window = False

        def _add_usage(diff):
            flav = last_state['flavor']
            usage_dict[flav] = usage_dict.get(flav, 0) + diff.total_seconds()

        for val in state[1:]:
            if last_state["status"] in tracked:
                diff = val["timestamp"] - last_timestamp
                if val['timestamp'] > last_timestamp:
                    # if diff < 0 then we were looking back before the start
                    # of the window.
                    _add_usage(diff)
                    last_timestamp = val['timestamp']
                    seen_sample_in_window = True

            last_state = val

        # extend the last state we know about, to the end of the window,
        # if we saw any actual uptime.
        if (end and last_state['status'] in tracked
                and seen_sample_in_window):
            diff = end - last_timestamp
            _add_usage(diff)

        # map the flavors to names on the way out
        return {helpers.flavor_name(f): v for f, v in usage_dict.items()}

    def _clean_entry(self, entry):
        result = {
            'status': entry['resource_metadata'].get(
                'status', entry['resource_metadata'].get(
                    'state', ""
                )
            ),
            'flavor': entry['resource_metadata'].get(
                'flavor.id', entry['resource_metadata'].get(
                    'instance_flavor_id', 0
                )
            ),
            'timestamp': entry['timestamp']
        }
        return result


class FromImage(Transformer):
    """
    Transformer for creating Volume entries from instance metadata.
    Checks if image was booted from image, and finds largest root
    disk size among entries.
    This relies heaviliy on instance metadata.
    """

    def _transform_usage(self, name, data, start, end):
        checks = config.transformers['from_image']['md_keys']
        none_values = config.transformers['from_image']['none_values']
        service = config.transformers['from_image']['service']
        size_sources = config.transformers['from_image']['size_keys']

        size = 0
        for entry in data:
            for source in checks:
                try:
                    if (entry['resource_metadata'][source] in none_values):
                        return None
                    break
                except KeyError:
                    pass
            for source in size_sources:
                try:
                    root_size = float(entry['resource_metadata'][source])
                    if root_size > size:
                        size = root_size
                except KeyError:
                    pass
        hours = (end - start).total_seconds() / 3600.0
        return {service: size * hours}


class GaugeMax(Transformer):
    """
    Transformer for max-integration of a gauge value over time.
    If the raw unit is 'gigabytes', then the transformed unit is
    'gigabyte-hours'.
    """

    def _transform_usage(self, name, data, start, end):
        max_vol = max([v["counter_volume"] for v in data]) if len(data) else 0
        if max_vol is None:
            max_vol = 0
            log.warning("None max_vol value for %s in window: %s - %s " %
                        (name, start.strftime(iso_time),
                         end.strftime(iso_time)))
        hours = (end - start).total_seconds() / 3600.0
        return {name: max_vol * hours}


class StorageMax(Transformer):
    """
    Variantion on the GaugeMax Transformer that checks for
    volume_type and uses that as the service, or uses the
    default service name.
    """

    def _transform_usage(self, name, data, start, end):

        if not data:
            return None

        max_vol = max([v["counter_volume"] for v in data])

        if max_vol is None:
            max_vol = 0
            log.warning("None max_vol value for %s in window: %s - %s " %
                        (name, start.strftime(iso_time),
                         end.strftime(iso_time)))

        if "volume_type" in data[-1]['resource_metadata']:
            vtype = data[-1]['resource_metadata']['volume_type']
            service = helpers.volume_type(vtype)
            if not service:
                service = name
        else:
            service = name

        hours = (end - start).total_seconds() / 3600.0
        return {service: max_vol * hours}


class GaugeSum(Transformer):
    """
    Transformer for sum-integration of a gauge value for given period.
    """
    def _transform_usage(self, name, data, start, end):
        sum_vol = 0
        for sample in data:
            t = sample['timestamp']
            if t >= start and t < end and sample["counter_volume"]:
                sum_vol += sample["counter_volume"]
        return {name: sum_vol}


class GaugeNetworkService(Transformer):
    """Transformer for Neutron network service, such as LBaaS, VPNaaS,
    FWaaS, etc.
    """

    def _transform_usage(self, name, data, start, end):
        # NOTE(flwang): The network service pollster of Ceilometer is using
        # status as the volume(see https://github.com/openstack/ceilometer/
        # blob/master/ceilometer/network/services/vpnaas.py#L55), so we have
        # to check the volume to make sure only the active service is
        # charged(0=inactive, 1=active).
        volumes = [v["counter_volume"] for v in data
                   if v["counter_volume"] < 2]
        max_vol = max(volumes) if len(volumes) else 0
        hours = (end - start).total_seconds() / 3600.0
        return {name: max_vol * hours}

# Transformer dict for us with the config.
# All usable transformers need to be here.
active_transformers = {
    'Uptime': Uptime,
    'InstanceUptime': InstanceUptime,
    'StorageMax': StorageMax,
    'GaugeMax': GaugeMax,
    'GaugeSum': GaugeSum,
    'FromImage': FromImage,
    'GaugeNetworkService': GaugeNetworkService
}
