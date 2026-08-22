from odoo.tests import tagged

from .common import TestInterCompanySalePurchaseCommon


@tagged("post_install", "-at_install")
class TestPoToSo(TestInterCompanySalePurchaseCommon):

    def test_po_creates_draft_so(self):
        po = (
            self.env["purchase.order"]
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
                                "product_qty": 2.0,
                                "price_unit": 80.0,
                                "product_uom": self.product.uom_id.id,
                            },
                        )
                    ],
                }
            )
        )
        po.with_company(self.company_a).button_confirm()
        so = self.env["sale.order"].sudo().search(
            [("auto_purchase_order_id", "=", po.id)], limit=1
        )
        self.assertTrue(so)
        self.assertTrue(so.auto_generated)
        self.assertEqual(so.company_id, self.company_b)
        self.assertEqual(so.partner_id, self.company_a.partner_id)
        self.assertEqual(so.state, "draft")
        self.assertEqual(len(so.order_line), 1)
        self.assertEqual(so.order_line.product_uom_qty, 2.0)

    def test_po_creates_confirmed_so(self):
        self.company_b.ic_so_state = "confirmed"
        po = (
            self.env["purchase.order"]
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
                                "product_qty": 1.0,
                                "price_unit": 50.0,
                                "product_uom": self.product.uom_id.id,
                            },
                        )
                    ],
                }
            )
        )
        po.with_company(self.company_a).button_confirm()
        so = self.env["sale.order"].sudo().search(
            [("auto_purchase_order_id", "=", po.id)], limit=1
        )
        self.assertEqual(so.state, "sale")
