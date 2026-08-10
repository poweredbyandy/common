from odoo import Command
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPbaRestrictQtyZero(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Restrict Qty Partner"})
        cls.warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)],
            limit=1,
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Restrict Qty Product",
                "is_storable": True,
                "list_price": 10.0,
                "type": "consu",
            }
        )

    def _set_qty(self, qty):
        self.env["stock.quant"]._update_available_quantity(
            self.product,
            self.warehouse.lot_stock_id,
            qty,
        )
        self.product.invalidate_recordset()

    def _create_order(self, qty):
        return self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": self.warehouse.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": qty,
                        }
                    )
                ],
            }
        )

    def test_confirm_allows_exact_available_qty(self):
        self._set_qty(1.0)
        order = self._create_order(1.0)
        self.assertFalse(order._pba_restrict_qty_zero_confirmation_error())
        order.action_confirm()
        self.assertEqual(order.state, "sale")

    def test_confirm_blocks_when_no_stock(self):
        order = self._create_order(1.0)
        error = order._pba_restrict_qty_zero_confirmation_error()
        self.assertTrue(error)
        with self.assertRaises(UserError):
            order.action_confirm()

    def test_confirm_aggregates_lines_of_same_product(self):
        self._set_qty(1.0)
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "warehouse_id": self.warehouse.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 1.0,
                        }
                    ),
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 1.0,
                        }
                    ),
                ],
            }
        )
        self.assertTrue(order._pba_restrict_qty_zero_confirmation_error())
