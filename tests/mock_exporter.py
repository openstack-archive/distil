from artifice import sales_order


class MockExporter(sales_order.SalesOrder):
    def _bill(self, tenant):
        pass

    def close(self):
        pass
