from datetime import datetime

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProductLastCost(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "PBA Cost Vendor"})
        cls.product = cls.env["product.product"].create(
            {"name": "PBA Last Cost Product"}
        )

    def test_last_cost_uses_purchase_order_date(self):
        order_date = datetime(2026, 6, 14, 12)
        approval_date = datetime(2026, 8, 6, 12)
        order = self.env["purchase.order"].create(
            {
                "partner_id": self.partner.id,
                "date_order": order_date,
            }
        )
        line = self.env["purchase.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "product_qty": 1.0,
            }
        )
        order.write(
            {
                "state": "purchase",
                "date_approve": approval_date,
            }
        )

        conversion_date = (
            self.product.product_tmpl_id._pba_last_purchase_line_conversion_date(
                line
            )
        )

        self.assertEqual(conversion_date, order_date.date())

    def test_last_cost_fallback_standard_price(self):
        tmpl = self.product.product_tmpl_id
        tmpl.standard_price = 40.0
        self.assertAlmostEqual(tmpl.pba_last_cost, 40.0)
        self.assertFalse(tmpl.pba_last_cost_manual)

    def test_last_cost_manual_write_is_kept(self):
        tmpl = self.product.product_tmpl_id
        tmpl.write({"standard_price": 40.0, "pba_last_cost": 55.0})
        self.assertAlmostEqual(tmpl.pba_last_cost, 55.0)
        self.assertTrue(tmpl.pba_last_cost_manual)
        tmpl.invalidate_recordset(["pba_last_cost"])
        self.assertAlmostEqual(tmpl.pba_last_cost, 55.0)

    def test_last_cost_manual_updates_dependent_amounts(self):
        tmpl = self.product.product_tmpl_id
        tmpl.write(
            {
                "standard_price": 100.0,
                "pba_cost_freight_percent": 0.1,
                "pba_last_cost": 80.0,
            }
        )
        self.assertAlmostEqual(tmpl.pba_cost_freight, 8.0)

    def test_confirmed_purchase_replaces_manual_last_cost(self):
        tmpl = self.product.product_tmpl_id
        tmpl.write({"standard_price": 40.0, "pba_last_cost": 55.0})
        order = self.env["purchase.order"].create({"partner_id": self.partner.id})
        self.env["purchase.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "product_qty": 1.0,
                "price_unit": 70.0,
            }
        )
        order.button_confirm()
        self.assertFalse(tmpl.pba_last_cost_manual)
        self.assertAlmostEqual(tmpl.pba_last_cost, 70.0)

