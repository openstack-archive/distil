import datetime
import constants
import helpers
import config


class TransformerValidationError(Exception):
    pass


class Transformer(object):

    meter_type = None
    required_meters = []

    def transform_usage(self, meters, start, end):
        self.validate_meters(meters)
        return self._transform_usage(meters, start, end)

    def validate_meters(self, meters):
        if self.meter_type is None:
            for meter in self.required_meters:
                if meter not in meters:
                    raise TransformerValidationError(
                        "Required meters: " +
                        str(self.required_meters))
        else:
            for meter in meters.values():
                if meter.type != self.meter_type:
                    raise TransformerValidationError(
                        "Meters must all be of type: " +
                        self.meter_type)

    def _transform_usage(self, meters, start, end):
        raise NotImplementedError


class Uptime(Transformer):
    """
    Transformer to calculate uptime based on states,
    which is broken apart into flavor at point in time.
    """
    required_meters = ['state', 'flavor']

    def _transform_usage(self, meters, start, end):
        # get tracked states from config
        tracked = config.transformers['uptime']['tracked_states']

        tracked_states = {constants.states[i] for i in tracked}

        usage_dict = {}

        state = meters['state']
        flavor = meters['flavor']

        def sort_and_clip_end(usage):
            parsed = (self._parse_timestamp(s) for s in usage)
            clipped = (s for s in parsed if not end or s['timestamp'] < end)
            return sorted(clipped, key=lambda x: x['timestamp'])

        state = sort_and_clip_end(state.usage())
        flavor = sort_and_clip_end(flavor.usage())

        if not len(state) or not len(flavor):
            # there was no data for this period.
            return usage_dict

        last_state = state[0]
        last_flavor = flavor[0]

        count = 1

        for val in state[1:]:
            if last_state["counter_volume"] in tracked_states:
                diff = val["timestamp"] - last_state["timestamp"]

                try:
                    flav = helpers.flavor_name(last_flavor['counter_volume'])
                    usage_dict[flav] = usage_dict[flav] + diff.seconds
                except KeyError:
                    usage_dict[flav] = diff.seconds

            last_state = val

            try:
                new_flavor = flavor[count]
                if new_flavor["timestamp"] <= last_state["timestamp"]:
                    count += 1
                    last_flavor = new_flavor
            except IndexError:
                # means this is the last flavor value, so no need to worry
                # about new_flavor or count
                pass

        # extend the last state we know about, to the end of the window
        if end and last_state['counter_volume'] in tracked_states:
            diff = end - last_state['timestamp']
            flav = helpers.flavor_name(last_flavor['counter_volume'])
            try:
                flav = helpers.flavor_name(last_flavor['counter_volume'])
                usage_dict[flav] = usage_dict[flav] + diff.seconds
            except KeyError:
                usage_dict[flav] = diff.seconds

        return usage_dict

    def _parse_timestamp(self, entry):
        result = {}
        result.update(entry)
        try:
            result['timestamp'] = datetime.datetime.strptime(result['timestamp'],
                    constants.date_format)
        except ValueError:
            result['timestamp'] = datetime.datetime.strptime(result['timestamp'],
                    constants.other_date_format)
        return result


class GaugeMax(Transformer):
    """
    Transformer that simply returns the highest value
    in the given range.
    """
    meter_type = 'gauge'

    def _transform_usage(self, meters, start, end):
        usage_dict = {}
        for name, meter in meters.iteritems():
            usage = meter.usage()
            max_vol = max([v["counter_volume"] for v in usage])
            usage_dict[name] = max_vol
        return usage_dict


class CumulativeRange(Transformer):
    """
    Transformer to get the usage over a given range in a cumulative
    metric, while taking into account that the metric can reset.
    """
    meter_type = 'cumulative'

    def _transform_usage(self, meters, start, end):
        usage_dict = {}
        for name, meter in meters.iteritems():
            measurements = meter.usage()
            measurements = sorted(measurements, key=lambda x: x["timestamp"])
            count = 0
            usage = 0
            last_measure = None
            for measure in measurements:
                if (last_measure is not None and
                        (measure["counter_volume"] <
                            last_measure["counter_volume"])):
                    usage = usage + last_measure["counter_volume"]
                count = count + 1
                last_measure = measure

            usage = usage + measurements[-1]["counter_volume"]

            if count > 1:
                total_usage = usage - measurements[0]["counter_volume"]
                usage_dict[name] = total_usage
        return usage_dict
