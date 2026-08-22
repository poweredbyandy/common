from odoo.tests import tagged

from .common import TestInterCompanySalePurchaseCommon


@tagged("post_install", "-at_install")
class TestPickingInvoice(TestInterCompanySalePurchaseCommon):

    def test_invoice_creates_draft_bill(self):
        self.company_b.ic_invoice_mode = "draft"
        invoice = (
            self.env["account.move"]
            .with_company(self.company_a)
            .create(
                {
                    "move_type": "out_invoice",
                    "partner_id": self.company_b.partner_id.id,
                    "company_id": self.company_a.id,
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": self.product.id,
                                "name": self.product.name,
                                "quantity": 1.0,
                                "price_unit": 100.0,
                            },
                        )
                    ],
                }
            )
        )
        invoice.action_post()
        bill = self.env["account.move"].sudo().search(
            [("auto_invoice_id", "=", invoice.id)], limit=1
        )
        self.assertTrue(bill)
        self.assertTrue(bill.auto_generated)
        self.assertEqual(bill.move_type, "in_invoice")
        self.assertEqual(bill.company_id, self.company_b)
        self.assertEqual(bill.state, "draft")

    def test_invoice_creates_posted_bill(self):
        self.company_b.ic_invoice_mode = "posted"
        invoice = (
            self.env["account.move"]
            .with_company(self.company_a)
            .create(
                {
                    "move_type": "out_invoice",
                    "partner_id": self.company_b.partner_id.id,
                    "company_id": self.company_a.id,
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": self.product.id,
                                "name": self.product.name,
                                "quantity": 1.0,
                                "price_unit": 100.0,
                            },
                        )
                    ],
                }
            )
        )
        invoice.action_post()
        bill = self.env["account.move"].sudo().search(
            [("auto_invoice_id", "=", invoice.id)], limit=1
        )
        self.assertEqual(bill.state, "posted")
