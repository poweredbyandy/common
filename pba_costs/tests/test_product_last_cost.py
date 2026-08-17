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
