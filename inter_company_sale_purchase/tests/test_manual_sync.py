from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import TestInterCompanySalePurchaseCommon


@tagged("post_install", "-at_install")
class TestManualSync(TestInterCompanySalePurchaseCommon):

    def test_manual_sync_po_when_not_linked(self):
        po = (
            self.env["purchase.order"]
            .with_company(self.company_a)
            .with_context(skip_ic_po_create_sync=True)
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
                                "product_qty": 3.0,
                                "price_unit": 40.0,
                                "product_uom": self.product.uom_id.id,
                            },
                        )
                    ],
                }
            )
        )
        self.assertFalse(po.sudo().ic_sale_order_id)
        self.assertTrue(po.ic_show_sync_button)
        action = po.action_ic_sync_sale_order()
        self.assertEqual(action["type"], "ir.actions.client")
        so = po.sudo().ic_sale_order_id
        self.assertTrue(so)
        self.assertEqual(so.company_id, self.company_b)
        self.assertEqual(so.state, "draft")
        self.assertFalse(po.ic_show_sync_button)
        with self.assertRaises(UserError):
            po.action_ic_sync_sale_order()

    def test_manual_sync_so_when_not_linked(self):
        so = (
            self.env["sale.order"]
            .with_company(self.company_b)
            .create(
                {
                    "partner_id": self.company_a.partner_id.id,
                    "company_id": self.company_b.id,
                    "order_line": [
                        (
                            0,
                            0,
                            {
                                "product_id": self.product.id,
                                "name": self.product.name,
                                "product_uom_qty": 2.0,
                                "price_unit": 55.0,
                                "product_uom": self.product.uom_id.id,
                            },
                        )
                    ],
                }
            )
        )
        self.assertFalse(so.sudo().ic_purchase_order_id)
        self.assertTrue(so.ic_show_sync_button)
        action = so.action_ic_sync_purchase_order()
        self.assertEqual(action["type"], "ir.actions.client")
        po = so.sudo().ic_purchase_order_id
        self.assertTrue(po)
        self.assertEqual(po.company_id, self.company_a)
        self.assertEqual(po.state, "draft")
        self.assertFalse(so.ic_show_sync_button)
        with self.assertRaises(UserError):
            so.action_ic_sync_purchase_order()
