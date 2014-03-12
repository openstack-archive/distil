import datetime
from artifice import constants


class Transformer(object):

    meter_type = None
    required_meters = []

    def transform_usage(self, meters):
        self.validate_meters(meters)
        return self._transform_usage(meters)

    def validate_meters(self, meters):
        if self.meter_type is None:
            for meter in meters.values():
                if meter.name not in self.required_meters:
                    raise AttributeError("Required meters: " +
                                         str(self.required_meters))
        else:
            for meter in meters.values():
                if meter.type != self.meter_type:
                    raise AttributeError("Meters must all be of type: " +
                                         self.meter_type)

    def _transform_usage(self, meters):
        raise NotImplementedError


class Uptime(Transformer):
    required_meters = ['state']
    # required_meters = ['state', 'flavor']

    def _transform_usage(self, meters):
        # this NEEDS to be moved to a config file
        tracked_states = [constants.active, constants.building,
                          constants.paused, constants.rescued,
                          constants.resized]
        usage_dict = {}

        state = meters['state']

        usage = sorted(state.usage(), key=lambda x: x["timestamp"])

        last = usage[0]
        try:
            last["timestamp"] = datetime.datetime.strptime(last["timestamp"],
                                                           constants.date_format)
        except ValueError:
            last["timestamp"] = datetime.datetime.strptime(last["timestamp"],
                                                           constants.other_date_format)
        except TypeError:
            pass

        uptime = 0.0

        for val in usage[1:]:
            try:
                val["timestamp"] = datetime.datetime.strptime(val["timestamp"],
                                                              constants.date_format)
            except ValueError:
                val["timestamp"] = datetime.datetime.strptime(val["timestamp"],
                                                              constants.other_date_format)
            except TypeError:
                pass

            if val["counter_volume"] in tracked_states:
                difference = val["timestamp"] - last["timestamp"]

                uptime = uptime + difference.seconds

            last = val

        usage_dict['flavor1'] = uptime

        return usage_dict


class GaugeMax(Transformer):
    meter_type = 'gauge'

    def _transform_usage(self, meters):
        usage_dict = {}
        for meter in meters.values():
            usage = meter.usage()
            max_vol = max([v["counter_volume"] for v in usage])
            usage_dict[meter.name] = max_vol
        return usage_dict


class GaugeAverage(Transformer):
    meter_type = 'gauge'

    def _transform_usage(self, meters):
        usage_dict = {}
        for meter in meters.values():
            usage = meter.usage()
            length = len(usage)
            avg_vol = sum([v["counter_volume"] for v in usage]) / length
            usage_dict[meter.name] = avg_vol
        return usage_dict


class CumulativeTotal(Transformer):
    meter_type = 'cumulative'

    def _transform_usage(self, meters):
        usage_dict = {}
        for meter in meters.values():
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
                usage_dict[meter.name] = total_usage
        return usage_dict
