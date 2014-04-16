import datetime
import constants
import helpers
import config


class TransformerValidationError(Exception):
    pass


class Transformer(object):
    def transform_usage(self, name, data, start, end):
        return self._transform_usage(name, data, start, end)

    def _transform_usage(self, name, data, start, end):
        raise NotImplementedError


class Uptime(Transformer):
    """
    Transformer to calculate uptime based on states,
    which is broken apart into flavor at point in time.
    """

    def _transform_usage(self, name, data, start, end):
        # get tracked states from config
        tracked = config.transformers['uptime']['tracked_states']

        tracked_states = {constants.states[i] for i in tracked}

        usage_dict = {}

        def sort_and_clip_end(usage):
            cleaned = (self._clean_entry(s) for s in usage)
            clipped = (s for s in cleaned if s['timestamp'] < end)
            return sorted(clipped, key=lambda x: x['timestamp'])

        state = sort_and_clip_end(data)

        if not len(state):
            # there was no data for this period.
            return usage_dict

        last_state = state[0]
        last_timestamp = max(start, last_state['timestamp'])

        count = 1

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

            last_state = val

        # extend the last state we know about, to the end of the window, if we saw any
        # actual uptime.
        if end and last_state['counter_volume'] in tracked_states and last_timestamp > start:
            diff = end - last_timestamp
            _add_usage(diff)

        # map the flavors to names on the way out
        return { helpers.flavor_name(f): v for f, v in usage_dict.items() }

    def _clean_entry(self, entry):
        result = {
            'counter_volume': entry['counter_volume'],
            'flavor': entry['resource_metadata'].get('flavor.id',
                entry['resource_metadata'].get('instance_flavor_id', 0))
        }
        try:
            result['timestamp'] = datetime.datetime.strptime(entry['timestamp'],
                    constants.date_format)
        except ValueError:
            result['timestamp'] = datetime.datetime.strptime(entry['timestamp'],
                    constants.other_date_format)
        return result


class GaugeMax(Transformer):
    """
    Transformer that simply returns the highest value
    in the given range.
    """
    meter_type = 'gauge'

    def _transform_usage(self, name, data, start, end):
        max_vol = max([v["counter_volume"] for v in data]) if len(data) else 0
        return {name: max_vol}
