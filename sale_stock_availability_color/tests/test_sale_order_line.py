from odoo import Command
from odoo.addons.sale.tests.common import TestSaleCommon
from odoo.tests import tagged


@tagged("post_install", "-at_install")
class TestSaleStockAvailabilityColor(TestSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)],
            limit=1,
        )
        cls.storable_product = cls.env["product.product"].create(
            {
                "name": "Availability Color Product",
                "is_storable": True,
                "list_price": 10.0,
                "type": "consu",
            }
        )

    def _create_sale_line(self, qty):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner_a.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.storable_product.id,
                            "product_uom_qty": qty,
                        }
                    )
                ],
            }
        )
        return order.order_line

    def _add_on_hand(self, qty):
        self.env["stock.quant"]._update_available_quantity(
            self.storable_product,
            self.warehouse.lot_stock_id,
            qty,
        )

    def _add_incoming(self, qty):
        move = self.env["stock.move"].create(
            {
                "location_dest_id": self.warehouse.lot_stock_id.id,
                "location_id": self.env.ref("stock.stock_location_suppliers").id,
                "name": "Incoming forecast",
                "picking_type_id": self.warehouse.in_type_id.id,
                "product_id": self.storable_product.id,
                "product_uom": self.storable_product.uom_id.id,
                "product_uom_qty": qty,
            }
        )
        move._action_confirm()
        return move

    def test_in_stock_is_green(self):
        self._add_on_hand(10)
        line = self._create_sale_line(5)
        self.assertEqual(line.qty_availability_state, "in_stock")

    def test_forecasted_only_is_orange(self):
        self._add_incoming(10)
        line = self._create_sale_line(5)
        self.assertFalse(line.qty_available_today)
        self.assertGreaterEqual(line.virtual_available_at_date, 5)
        self.assertEqual(line.qty_availability_state, "forecasted")

    def test_no_stock_no_forecast_is_red(self):
        line = self._create_sale_line(5)
        self.assertEqual(line.qty_availability_state, "unavailable")
