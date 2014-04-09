import mock
from artifice import interface, models, config
from .data_samples import RESOURCES, MAPPINGS
from .constants import TENANTS, AUTH_TOKEN
from datetime import timedelta
import json


@mock.patch("artifice.auth.Keystone")
@mock.patch("sqlalchemy.create_engine")
def get_usage(start, end, sqlmock, Keystone):

    # At this point, we prime the ceilometer/requests response
    # system, so that what we return to usage is what we expect
    # to get in the usage system.
    Keystone.auth_token = AUTH_TOKEN

    def get_meter(self, start, end, auth):
        # Returns meter data from our data up above
        data = MAPPINGS[self.link]
        return data

    interface.Meter.get_meter = get_meter
    artifice = interface.Artifice()
    artifice.auth.tenants.list.return_value = TENANTS

    Keystone.assert_called_with(
        username=config.auth["username"],
        password=config.auth["password"],
        tenant_name=config.auth["default_tenant"],
        auth_url=config.auth["end_point"],
        insecure=config.auth["insecure"]
    )
    tenants = None
    tenants = artifice.tenants

    t = tenants[0]  # First tenant
    t.resources = mock.create_autospec(interface.Resource, spec_set=True)
    t.resources.return_value = (RESOURCES["networks"] + RESOURCES["vms"] +
                                RESOURCES["objects"] + RESOURCES["volumes"] +
                                RESOURCES["ips"])

    # because of mocking, start/end dates are not required here:
    usage = t.usage(start=start, end=end)

    # This is a fully qualified Usage object.
    return usage


def fill_db(session, numb_tenants, numb_resources, now):
    for i in range(numb_tenants):
        session.add(models.Tenant(
            id="tenant_id_" + str(i),
            info="metadata",
            name="tenant_name_" + str(i),
            created=now
        ))
        for ii in range(numb_resources):
            session.add(models.Resource(
                id="resource_id_" + str(ii),
                info=json.dumps({"type": "Resource" + str(ii)}),
                tenant_id="tenant_id_" + str(i),
                created=now
            ))
            session.add(models.UsageEntry(
                service="service" + str(ii),
                volume=5,
                resource_id="resource_id_" + str(ii),
                tenant_id="tenant_id_" + str(i),
                start=(now - timedelta(days=30)),
                end=now,
                created=now
            ))
    session.commit()


def create_usage_entries(num_resources, num_services, volume):
    entries = []
    for i in range(num_resources):
        for ii in range(num_services):
            entry = mock.MagicMock()
            entry.volume = volume
            entry.service = "service" + str(ii)
            entry.resource_id = "resource_id_" + str(i)
            entries.append(entry)

    return entries
