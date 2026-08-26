from odoo.tests import tagged

from .common import TestInterCompanySalePurchaseCommon


@tagged("post_install", "-at_install")
class TestSoToPo(TestInterCompanySalePurchaseCommon):

    def test_draft_so_creates_draft_po_automatically(self):
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
                                "price_unit": 100.0,
                                "product_uom": self.product.uom_id.id,
                            },
                        )
                    ],
                }
            )
        )
        po = so.sudo().ic_purchase_order_id
        self.assertTrue(po)
        self.assertTrue(po.auto_generated)
        self.assertEqual(po.company_id, self.company_a)
        self.assertEqual(po.state, "draft")
        self.assertAlmostEqual(po.order_line.price_unit, 100.0)
        self.assertFalse(so.ic_show_sync_button)

    def test_so_price_change_updates_draft_po(self):
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
                                "price_unit": 100.0,
                                "product_uom": self.product.uom_id.id,
                            },
                        )
                    ],
                }
            )
        )
        po = so.sudo().ic_purchase_order_id
        self.assertTrue(po)
        so.with_company(self.company_b).with_context(
            allowed_company_ids=self.company_b.ids
        ).order_line.write({"price_unit": 175.0})
        self.assertAlmostEqual(po.sudo().order_line.price_unit, 175.0)

    def test_po_creates_so_and_so_price_updates_po(self):
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
        so = po.sudo().ic_sale_order_id
        self.assertTrue(so)
        so.with_company(self.company_b).with_context(
            allowed_company_ids=self.company_b.ids
        ).order_line.write({"price_unit": 155.0})
        self.assertAlmostEqual(po.sudo().order_line.price_unit, 155.0)

    def test_so_confirm_confirms_existing_draft_po(self):
        self.company_a.ic_po_state = "confirmed"
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
                                "product_uom_qty": 1.0,
                                "price_unit": 70.0,
                                "product_uom": self.product.uom_id.id,
                            },
                        )
                    ],
                }
            )
        )
        po = so.sudo().ic_purchase_order_id
        self.assertEqual(po.state, "draft")
        so.with_company(self.company_b).action_confirm()
        self.assertIn(po.sudo().state, ("purchase", "done"))

    def test_so_creates_draft_po(self):
        self.company_b.ic_po_state = "draft"
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
        po = so.sudo().ic_purchase_order_id
        self.assertTrue(po)
        self.assertEqual(po.state, "draft")
        so.with_company(self.company_a).action_confirm()
        self.assertEqual(po.sudo().state, "draft")
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
        po = so.sudo().ic_purchase_order_id
        self.assertEqual(po.state, "draft")
        so.with_company(self.company_a).action_confirm()
        self.assertIn(po.sudo().state, ("purchase", "done"))
