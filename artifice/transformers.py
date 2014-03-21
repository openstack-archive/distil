import datetime
import constants
import helpers


class TransformerValidationError(BaseException):
    pass


class Transformer(object):

    meter_type = None
    required_meters = []

    def transform_usage(self, meters):
        self.validate_meters(meters)
        return self._transform_usage(meters)

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

    def _transform_usage(self, meters):
        raise NotImplementedError


class Uptime(Transformer):
    required_meters = ['state', 'flavor']

    def _transform_usage(self, meters):
        # this NEEDS to be moved to a config file
        tracked_states = [constants.active, constants.building,
                          constants.paused, constants.rescued,
                          constants.resized]
        usage_dict = {}

        state = meters['state']
        flavor = meters['flavor']

        state = sorted(state.usage(), key=lambda x: x["timestamp"])
        flavor = sorted(flavor.usage(), key=lambda x: x["timestamp"])

        if not len(state) or not len(flavor):
            # there was no data for this period.
            return usage_dict

        last_state = state[0]
        self.parse_timestamp(last_state)

        last_flavor = flavor[0]
        self.parse_timestamp(last_flavor)

        count = 1

        for val in state[1:]:
            self.parse_timestamp(val)

            if last_state["counter_volume"] in tracked_states:
                diff = val["timestamp"] - last_state["timestamp"]

                try:
                    flav = helpers.flavor_name(last_flavor['counter_volume'])
                    print flav
                    usage_dict[flav] = usage_dict[flav] + diff.seconds
                except KeyError:
                    usage_dict[flav] = diff.seconds

            last_state = val

            try:
                new_flavor = flavor[count]
                self.parse_timestamp(new_flavor)
                if new_flavor["timestamp"] <= last_state["timestamp"]:
                    count += 1
                    last_flavor = new_flavor
            except IndexError:
                # means this is the last flavor value, so no need to worry
                # about new_flavor or count
                pass
        return usage_dict

    def parse_timestamp(self, entry):
        try:
            entry["timestamp"] = datetime.datetime.\
                strptime(entry["timestamp"],
                         constants.date_format)
        except ValueError:
            entry["timestamp"] = datetime.datetime.\
                strptime(entry["timestamp"],
                         constants.other_date_format)
        except TypeError:
            pass


class GaugeMax(Transformer):
    meter_type = 'gauge'

    def _transform_usage(self, meters):
        usage_dict = {}
        for name, meter in meters.iteritems():
            usage = meter.usage()
            max_vol = max([v["counter_volume"] for v in usage])
            usage_dict[name] = max_vol
        return usage_dict


class CumulativeRange(Transformer):
    meter_type = 'cumulative'

    def _transform_usage(self, meters):
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
