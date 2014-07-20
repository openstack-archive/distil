import datetime
import constants
import helpers
import config


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
            )
        }
        try:
            result['timestamp'] = datetime.datetime.strptime(
                entry['timestamp'], constants.date_format)
        except ValueError:
            result['timestamp'] = datetime.datetime.strptime(
                entry['timestamp'], constants.other_date_format)
        return result


class GaugeMax(Transformer):
    """
    Transformer for max-integration of a gauge value over time.
    If the raw unit is 'gigabytes', then the transformed unit is
    'gigabyte-hours'.
    """

    def _transform_usage(self, name, data, start, end):
        max_vol = max([v["counter_volume"] for v in data]) if len(data) else 0
        hours = (end - start).total_seconds() / 3600.0
        return {name: max_vol * hours}


class GaugeSum(Transformer):
    """
    Transformer for sum-integration of a gauge value for given period.
    """
    def _transform_usage(self, name, data, start, end):
        sum_vol = 0
        for sample in data:
            t = datetime.datetime.strptime(sample['timestamp'],
                                           '%Y-%m-%dT%H:%M:%S.%f')
            if t >= start and t < end:
                sum_vol += sample["counter_volume"]
        return {name: sum_vol}


# Transformer dict for us with the config.
# All usable transformers need to be here.
active_transformers = {
    'Uptime': Uptime,
    'GaugeMax': GaugeMax,
    'GaugeSum': GaugeSum
}
