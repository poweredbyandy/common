from odoo.tests import tagged

from .common import TestInterCompanySalePurchaseCommon


@tagged("post_install", "-at_install")
class TestSoToPo(TestInterCompanySalePurchaseCommon):

    def test_so_creates_draft_po(self):
        so = (
            self.env["sale.order"]
            .with_company(self.company_a)
            .create(
                {
                    "partner_id": self.company_b.partner_id.id,
                    "company_id": self.company_a.id,
                    "order_line": [
                        (
                            0,
                            0,
                            {
                                "product_id": self.product.id,
                                "name": self.product.name,
                                "product_uom_qty": 3.0,
                                "price_unit": 120.0,
                                "product_uom": self.product.uom_id.id,
                            },
                        )
                    ],
                }
            )
        )
        so.with_company(self.company_a).action_confirm()
        po = self.env["purchase.order"].sudo().search(
            [("auto_sale_order_id", "=", so.id)], limit=1
        )
        self.assertTrue(po)
        self.assertTrue(po.auto_generated)
        self.assertEqual(po.company_id, self.company_b)
        self.assertEqual(po.partner_id, self.company_a.partner_id)
        self.assertEqual(po.state, "draft")
        self.assertEqual(po.order_line.product_qty, 3.0)

    def test_so_creates_confirmed_po(self):
        self.company_b.ic_po_state = "confirmed"
        so = (
            self.env["sale.order"]
            .with_company(self.company_a)
            .create(
                {
                    "partner_id": self.company_b.partner_id.id,
                    "company_id": self.company_a.id,
                    "order_line": [
                        (
                            0,
                            0,
                            {
                                "product_id": self.product.id,
                                "name": self.product.name,
                                "product_uom_qty": 1.0,
                                "price_unit": 90.0,
                                "product_uom": self.product.uom_id.id,
                            },
                        )
                    ],
                }
            )
        )
        so.with_company(self.company_a).action_confirm()
        po = self.env["purchase.order"].sudo().search(
            [("auto_sale_order_id", "=", so.id)], limit=1
        )
        self.assertIn(po.state, ("purchase", "done"))
