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

import copy
from datetime import datetime

from distil.transformer import BaseTransformer
from distil.common import constants
from distil.common import openstack


class UpTimeTransformer(BaseTransformer):
    """
    Transformer to calculate uptime based on states,
    which is broken apart into flavor at point in time.
    """

    def _wash_data(self, entries, tracked):
        """Get rid of invalid entries."""
        copy_entries = copy.deepcopy(entries)

        for entry in copy_entries:
            status = entry['metadata'].get(
                'status', entry['metadata'].get('state', "")
            )
            if status not in tracked:
                entries.remove(entry)

    def _transform_usage(self, name, data, start, end):
        # get tracked states from config
        tracked = self.config['uptime']['tracked_states']

        usage_dict = {}

        def sort_and_clip_end(usage):
            cleaned = (self._clean_entry(s) for s in usage)
            clipped = [s for s in cleaned if s['timestamp'] < end]
            return clipped

        state = sort_and_clip_end(data)

        self._wash_data(data, tracked)

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
                if val['timestamp'] > last_timestamp:
                    # if diff < 0 then we were looking back before the start
                    # of the window.
                    diff = val["timestamp"] - last_timestamp
                    _add_usage(diff)

                    last_timestamp = val['timestamp']
                    seen_sample_in_window = True

            last_state = val

        # extend the last state we know about, to the end of the window,
        # if we saw any actual uptime.
        if (end and last_state['status'] in tracked and seen_sample_in_window):
            diff = end - last_timestamp
            _add_usage(diff)

        return usage_dict

    def _clean_entry(self, entry):
        try:
            timestamp = datetime.strptime(
                entry['timestamp'], constants.date_format)
        except ValueError:
            timestamp = datetime.strptime(
                entry['timestamp'], constants.date_format_f)

        result = {
            'status': entry['metadata'].get(
                'status', entry['metadata'].get('state', "")
            ),
            'flavor': entry['metadata'].get('instance_type'),
            'timestamp': timestamp
        }

        return result


class FromImageTransformer(BaseTransformer):
    """
    Transformer for creating Volume entries from instance metadata.
    Checks if image was booted from image, and finds largest root
    disk size among entries.
    This relies heaviliy on instance metadata.
    """

    def _transform_usage(self, name, data, start, end):
        checks = self.config['from_image']['md_keys']
        none_values = self.config['from_image']['none_values']
        service = self.config['from_image']['service']
        size_sources = self.config['from_image']['size_keys']

        size = 0
        for entry in data:
            for source in checks:
                try:
                    if (entry['metadata'][source] in none_values):
                        return None
                    break
                except KeyError:
                    pass
            for source in size_sources:
                try:
                    root_size = float(entry['metadata'][source])
                    if root_size > size:
                        size = root_size
                except KeyError:
                    pass

        hours = (end - start).total_seconds() / 3600.0

        return {service: size * hours}


class NetworkServiceTransformer(BaseTransformer):
    """Transformer for Neutron network service, such as LBaaS, VPNaaS,
    FWaaS, etc.
    """

    def _transform_usage(self, name, data, start, end):
        # NOTE(flwang): The network service pollster of Ceilometer is using
        # status as the volume(see https://github.com/openstack/ceilometer/
        # blob/master/ceilometer/network/services/vpnaas.py#L55), so we have
        # to check the volume to make sure only the active service is
        # charged(0=inactive, 1=active).
        volumes = [v["volume"] for v in data if
                   v["volume"] < 2]
        max_vol = max(volumes) if len(volumes) else 0
        hours = (end - start).total_seconds() / 3600.0
        return {name: max_vol * hours}
