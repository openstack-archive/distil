from . import test_interface, helpers
from artifice import database
from artifice.models import billing
from datetime import timedelta


class TestBillableModels(test_interface.TestInterface):

    def test_build_billable(self):
        """Test to return a billable tenant object,
           and that the object data matches that put into the DB."""
        numb_resources = 24
        numb_tenants = 5

        helpers.fill_db(self.session, numb_tenants, numb_resources, self.end)

        db = database.Database(self.session)

        for i in range(numb_tenants):
            usage = db.usage(self.start, self.start + timedelta(days=60),
                             "tenant_id_" + str(i))
            billable = billing.build_billable(usage, self.session)

            self.assertEquals(len(billable.resources.values()), numb_resources)
            self.assertEquals(billable.name, "tenant_name_" + str(i))
            self.assertEquals(billable.id, "tenant_id_" + str(i))

            for ii in range(numb_resources):
                res_id = "resource_id_" + str(ii)
                resource = billable.resources[res_id]
                self.assertEquals(len(resource.services.values()), 1)
                serv_name = "service" + str(ii)
                self.assertEquals(resource.services[serv_name].volume, 5)
