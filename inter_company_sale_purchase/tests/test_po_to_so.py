from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import TestInterCompanySalePurchaseCommon


@tagged("post_install", "-at_install")
class TestPoToSo(TestInterCompanySalePurchaseCommon):

    def test_draft_po_creates_draft_so(self):
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
        so = po.ic_sale_order_id
        self.assertTrue(so)
        self.assertTrue(so.auto_generated)
        self.assertEqual(so.company_id, self.company_b)
        self.assertEqual(so.partner_id, self.company_a.partner_id)
        self.assertEqual(so.state, "draft")
        self.assertEqual(po.state, "draft")
        self.assertEqual(len(so.order_line), 1)
        self.assertEqual(so.order_line.product_uom_qty, 2.0)

    def test_ic_purchase_confirm_blocked_without_setting(self):
        self.company_a.ic_allow_confirm_ic_purchase = False
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
        self.assertTrue(po.ic_sale_order_id)
        self.assertEqual(po.ic_sale_order_id.state, "draft")
        with self.assertRaises(UserError) as error:
            po.with_company(self.company_a).button_confirm()
        self.assertIn("cannot be confirmed", str(error.exception).lower())

    def test_po_confirm_can_confirm_so(self):
        self.company_a.ic_allow_confirm_ic_purchase = True
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
        self.assertEqual(po.ic_sale_order_id.state, "draft")
        po.with_company(self.company_a).button_confirm()
        self.assertEqual(po.ic_sale_order_id.state, "sale")
