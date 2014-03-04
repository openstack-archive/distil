import datetime
from constants import date_format, other_date_format


class Artifact(object):

    """
    Provides base artifact controls; generic typing information
    for the artifact structures.
    """

    def __init__(self, resource, usage, start, end):

        self.resource = resource
        self.usage = usage  # Raw meter data from Ceilometer
        self.start = start
        self.end = end

    def __getitem__(self, item):
        if item in self._data:
            return self._data[item]
        raise KeyError("no such item %s" % item)

    def volume(self):
        """
        Default billable number for this volume
        """
        return sum([x["counter_volume"] for x in self.usage])


class Cumulative(Artifact):

    def volume(self):
        measurements = self.usage
        measurements = sorted(measurements, key=lambda x: x["timestamp"])
        count = 0
        usage = 0
        last_measure = None
        for measure in measurements:
            if last_measure is not None and (measure["counter_volume"] <
                                             last_measure["counter_volume"]):
                usage = usage + last_measure["counter_volume"]
            count = count + 1
            last_measure = measure

        usage = usage + measurements[-1]["counter_volume"]

        if count > 1:
            total_usage = usage - measurements[0]["counter_volume"]
        return total_usage


# Gauge and Delta have very little to do: They are expected only to
# exist as "not a cumulative" sort of artifact.
class Gauge(Artifact):

    def volume(self):
        """
        Default billable number for this volume
        """
        # print "Usage is %s" % self.usage
        usage = sorted(self.usage, key=lambda x: x["timestamp"])

        blocks = []
        curr = [usage[0]]
        last = usage[0]
        try:
            last["timestamp"] = datetime.datetime.strptime(last["timestamp"],
                                                           date_format)
        except ValueError:
            last["timestamp"] = datetime.datetime.strptime(last["timestamp"],
                                                           other_date_format)
        except TypeError:
            pass

        for val in usage[1:]:
            try:
                val["timestamp"] = datetime.datetime.strptime(val["timestamp"],
                                                              date_format)
            except ValueError:
                val["timestamp"] = datetime.datetime.strptime(val["timestamp"],
                                                              other_date_format)
            except TypeError:
                pass

            difference = (val['timestamp'] - last["timestamp"])
            if difference > datetime.timedelta(hours=1):
                blocks.append(curr)
                curr = [val]
                last = val
            else:
                curr.append(val)

        # this adds the last remaining values as a block of their own on exit
        # might mean people are billed twice for an hour at times...
        # but solves the issue of not billing if there isn't enough data for
        # full hour.
        blocks.append(curr)

        # We are now sorted into 1-hour blocks
        totals = []
        for block in blocks:
            usage = max([v["counter_volume"] for v in block])
            totals.append(usage)

        # totals = [max(x, key=lambda val: val["counter_volume"] ) for x in blocks]
        # totals is now an array of max values per hour for a given month.
        return sum(totals)

    # This continues to be wrong.
    def uptime(self, tracked):
        """Calculates uptime accurately for the given 'tracked' states.
        - Will ignore all other states.
        - Relies heavily on the existence of a state meter, and
          should only ever be called on the state meter.

        Returns: uptime in seconds"""

        usage = sorted(self.usage, key=lambda x: x["timestamp"])

        last = usage[0]
        try:
            last["timestamp"] = datetime.datetime.strptime(last["timestamp"],
                                                           date_format)
        except ValueError:
            last["timestamp"] = datetime.datetime.strptime(last["timestamp"],
                                                           other_date_format)
        except TypeError:
            pass

        uptime = 0.0

        for val in usage[1:]:
            try:
                val["timestamp"] = datetime.datetime.strptime(val["timestamp"],
                                                              date_format)
            except ValueError:
                val["timestamp"] = datetime.datetime.strptime(val["timestamp"],
                                                              other_date_format)
            except TypeError:
                pass

            if val["counter_volume"] in tracked:
                difference = val["timestamp"] - last["timestamp"]

                uptime = uptime + difference.seconds

            last = val

        return uptime


class Delta(Artifact):
    pass
