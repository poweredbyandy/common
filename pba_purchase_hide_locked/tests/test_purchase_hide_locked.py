from ast import literal_eval

from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPurchaseHideLocked(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.po_lock = "edit"
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Vendor Hide Locked",
                "supplier_rank": 1,
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Product Hide Locked",
                "purchase_ok": True,
                "list_price": 10.0,
            }
        )

    def _create_order(self):
        return self.env["purchase.order"].create(
            {
                "partner_id": self.partner.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "name": self.product.display_name,
                            "product_qty": 1.0,
                            "price_unit": 10.0,
                        }
                    )
                ],
            }
        )

    def test_purchase_orders_action_excludes_locked(self):
        action = self.env.ref("purchase.purchase_form_action")
        domain = literal_eval(action.domain)
        self.assertEqual(domain, [("state", "=", "purchase")])

        open_order = self._create_order()
        open_order.button_confirm()
        self.assertEqual(open_order.state, "purchase")

        locked_order = self._create_order()
        locked_order.button_confirm()
        locked_order.button_done()
        self.assertEqual(locked_order.state, "done")

        visible = self.env["purchase.order"].search(domain)
        self.assertIn(open_order, visible)
        self.assertNotIn(locked_order, visible)
