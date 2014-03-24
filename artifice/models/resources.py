from artifice import transformers


class BaseModelConstruct(object):

    def __init__(self, raw, start, end):
        # raw is the raw data for this
        self._raw = raw
        self._location = None
        self.start = start
        self.end = end

    @property
    def resource_id(self):
        return self._raw.resource.resource_id

    @property
    def tenant_id(self):
        return self._raw.resource.project_id

    @property
    def info(self):
        return {"type": self.type}

    def __getitem__(self, item):
        return self._raw[item]

    def meters(self):
        dct = {}
        for meter in self.relevant_meters:
            try:
                mtr = self._raw.meter(meter, self.start, self.end)
                dct[meter] = mtr
            except AttributeError:
                # This is OK. We're not worried about non-existent meters,
                # I think. For now, anyway.
                pass
        return dct

    def usage(self):
        meters = self.meters()
        usage = self.transformer.transform_usage(meters, self.start, self.end)
        return usage


class VM(BaseModelConstruct):
    relevant_meters = ["state", 'flavor']

    transformer = transformers.Uptime()

    type = "virtual_machine"

    @property
    def info(self):
        return {"name": self.name,
                "type": self.type}

    @property
    def memory(self):
        return self._raw["metadata"]["memory"]

    @property
    def cpus(self):
        return self._raw["metadata"]["vcpus"]

    @property
    def state(self):
        return self._raw["metadata"]["state"]

    @property
    def name(self):
        return self._raw["metadata"]["display_name"]

    @property
    def region(self):
        return self._raw["metadata"]["OS-EXT-AZ:availability_zone"]


class FloatingIP(BaseModelConstruct):

    relevant_meters = ["ip.floating"]

    transformer = transformers.GaugeMax()

    type = "floating_ip"


class Object(BaseModelConstruct):

    relevant_meters = ["storage.objects.size"]

    transformer = transformers.GaugeMax()

    type = "object_storage"


class Volume(BaseModelConstruct):

    relevant_meters = ["volume.size"]

    transformer = transformers.GaugeMax()

    type = "volume"

    @property
    def info(self):
        return {"name": self.name,
                "type": self.type}

    @property
    def name(self):
        return self._raw["metadata"]["display_name"]


class Network(BaseModelConstruct):
    relevant_meters = ["network.outgoing.bytes", "network.incoming.bytes"]

    transformer = transformers.CumulativeRange()

    type = "network_interface"
