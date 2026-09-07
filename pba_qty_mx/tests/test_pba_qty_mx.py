from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPbaQtyMx(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "PBA Qty MX Customer"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "PBA Qty MX Product",
                "list_price": 10.0,
                "sale_ok": True,
                "pba_qty_mx": 2.0,
            }
        )

    def test_mixin_rejects_decimal_quantity_for_integer_multiple(self):
        line = self.env["sale.order.line"]
        rounding = self.product.uom_id.rounding
        self.assertFalse(line._pba_qty_mx_is_valid(2.01, 2.0, rounding))
        self.assertFalse(line._pba_qty_mx_is_valid(3.0, 2.0, rounding))
        self.assertTrue(line._pba_qty_mx_is_valid(2.0, 2.0, rounding))
        self.assertTrue(line._pba_qty_mx_is_valid(4.0, 2.0, rounding))

    def test_sale_line_rejects_decimal_quantity(self):
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        with self.assertRaises(ValidationError):
            self.env["sale.order.line"].create(
                {
                    "order_id": order.id,
                    "product_id": self.product.id,
                    "product_uom_qty": 2.01,
                }
            )

    def test_sale_line_accepts_exact_multiple(self):
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        line = self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "product_uom_qty": 4.0,
            }
        )
        self.assertEqual(line.product_uom_qty, 4.0)

    def test_sale_line_write_rejects_decimal_quantity(self):
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        line = self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "product_uom_qty": 2.0,
            }
        )
        with self.assertRaises(ValidationError):
            line.write({"product_uom_qty": 2.01})

    def test_invoice_line_rejects_decimal_quantity(self):
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner.id,
            }
        )
        with self.assertRaises(ValidationError):
            self.env["account.move.line"].create(
                {
                    "move_id": move.id,
                    "product_id": self.product.id,
                    "quantity": 2.01,
                }
            )

    def test_catalog_does_not_preselect_multiple_product(self):
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        data = order._get_product_catalog_order_line_info([self.product.id])
        self.assertEqual(data[self.product.id].get("quantity") or 0, 0)
        self.assertEqual(data[self.product.id]["pba_qty_mx"], 2.0)

    def test_catalog_keeps_multiple_after_product_is_in_order(self):
        order = self.env["sale.order"].create({"partner_id": self.partner.id})
        self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "product_uom_qty": 2.0,
            }
        )
        data = order._get_product_catalog_order_line_info([self.product.id])
        self.assertEqual(data[self.product.id]["quantity"], 2.0)
        self.assertEqual(data[self.product.id]["pba_qty_mx"], 2.0)
