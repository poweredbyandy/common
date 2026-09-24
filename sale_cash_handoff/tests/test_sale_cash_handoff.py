from odoo.exceptions import UserError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestSaleCashHandoff(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.salesperson = new_test_user(
            cls.env,
            login="salesperson_cash_handoff",
            groups="sale_cash_handoff.group_salesperson",
        )
        cls.cashier = new_test_user(
            cls.env,
            login="cashier_cash_handoff",
            groups="sale_cash_handoff.group_cashier",
        )
        cls.partner = cls.env["res.partner"].create({"name": "Cliente caja"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "Producto caja",
                "list_price": 25.0,
                "sale_ok": True,
            }
        )

    def _create_quotation(self, user):
        return (
            self.env["sale.order"]
            .with_user(user)
            .create(
                {
                    "partner_id": self.partner.id,
                    "order_line": [
                        (
                            0,
                            0,
                            {
                                "product_id": self.product.id,
                                "product_uom_qty": 2,
                            },
                        )
                    ],
                }
            )
        )

    def test_salesperson_edits_until_sent_to_cash(self):
        order = self._create_quotation(self.salesperson)
        self.assertFalse(order.locked_for_salesman)
        self.assertFalse(order.is_salesman_locked)
        order.with_user(self.salesperson).write({"client_order_ref": "REF-1"})
        self.assertEqual(order.client_order_ref, "REF-1")

        order.with_user(self.salesperson).action_send_to_cash()
        self.assertTrue(order.locked_for_salesman)
        self.assertTrue(order.with_user(self.salesperson).is_salesman_locked)

        with self.assertRaises(UserError):
            order.with_user(self.salesperson).write({"client_order_ref": "REF-2"})
        with self.assertRaises(UserError):
            self.env["sale.order.line"].with_user(self.salesperson).create(
                {
                    "order_id": order.id,
                    "product_id": self.product.id,
                    "product_uom_qty": 1,
                }
            )
        with self.assertRaises(UserError):
            order.order_line.with_user(self.salesperson).write({"product_uom_qty": 5})
        with self.assertRaises(UserError):
            order.with_user(self.salesperson).action_confirm()

    def test_cashier_edits_confirms_and_returns(self):
        order = self._create_quotation(self.salesperson)
        order.with_user(self.salesperson).action_send_to_cash()

        order.with_user(self.cashier).write({"client_order_ref": "CAJA"})
        order.order_line.with_user(self.cashier).write({"product_uom_qty": 3, "discount": 10})
        self.assertEqual(order.client_order_ref, "CAJA")
        self.assertEqual(order.order_line.product_uom_qty, 3)
        self.assertFalse(order.with_user(self.cashier).is_salesman_locked)

        order.with_user(self.cashier).action_confirm()
        self.assertEqual(order.state, "sale")

        order.with_user(self.cashier).action_return_to_sales()
        self.assertFalse(order.locked_for_salesman)
        order.with_user(self.salesperson).write({"client_order_ref": "DEVUELTA"})
        self.assertEqual(order.client_order_ref, "DEVUELTA")

    def test_salesperson_cannot_return_to_sales(self):
        order = self._create_quotation(self.salesperson)
        order.with_user(self.salesperson).action_send_to_cash()
        with self.assertRaises(UserError):
            order.with_user(self.salesperson).action_return_to_sales()
        self.assertTrue(order.locked_for_salesman)
