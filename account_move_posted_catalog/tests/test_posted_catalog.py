from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestPostedCatalog(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_catalog = cls._create_product(
            name="Front seal",
            lst_price=30.0,
        )

    def test_catalog_adds_product_while_draft(self):
        move = self._create_invoice_one_line(price_unit=100.0, product_id=self.product_a)
        self.assertFalse(move._is_readonly())
        move._update_order_line_info(self.product_catalog.id, 1)
        self.assertIn(self.product_catalog, move.invoice_line_ids.product_id)

    def test_catalog_rejects_product_after_post_from_another_session(self):
        move = self._create_invoice_one_line(
            price_unit=100.0,
            product_id=self.product_a,
            post=True,
        )
        self.assertEqual(move.state, "posted")
        self.assertTrue(move._is_readonly())
        product_lines = move.invoice_line_ids.filtered(
            lambda line: line.display_type == "product"
        )

        with self.assertRaises(UserError):
            move._update_order_line_info(self.product_catalog.id, 1)
        with self.assertRaises(UserError):
            move._update_order_line_info(self.product_a.id, 5)
        with self.assertRaises(UserError):
            self.env["account.move.line"].create(
                {
                    "move_id": move.id,
                    "product_id": self.product_catalog.id,
                    "quantity": 1.0,
                }
            )

        self.assertEqual(
            move.invoice_line_ids.filtered(lambda line: line.display_type == "product"),
            product_lines,
        )
        self.assertEqual(
            product_lines.filtered(lambda line: line.product_id == self.product_a).quantity,
            1.0,
        )
