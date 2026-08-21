from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestPbaCostAccess(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "PBA Cost Access Vendor"})
        cls.product = cls.env["product.product"].create(
            {
                "name": "PBA Cost Access Product",
                "purchase_ok": True,
                "pba_cost_freight_percent": 0.1,
            }
        )
        cls.user_read = new_test_user(
            cls.env,
            login="pba_cost_read",
            groups=(
                "base.group_user,purchase.group_purchase_user,"
                "product.group_product_manager,"
                "pba_costs.group_pba_product_costs_tab"
            ),
        )
        cls.user_rfq = new_test_user(
            cls.env,
            login="pba_cost_rfq",
            groups=(
                "base.group_user,purchase.group_purchase_manager,"
                "product.group_product_manager,"
                "pba_costs.group_pba_costs_edit_rfq"
            ),
        )
        cls.user_all = new_test_user(
            cls.env,
            login="pba_cost_all",
            groups=(
                "base.group_user,purchase.group_purchase_manager,"
                "product.group_product_manager,"
                "pba_costs.group_pba_costs_edit_all"
            ),
        )

    def _create_rfq(self):
        order = self.env["purchase.order"].create({"partner_id": self.partner.id})
        line = self.env["purchase.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "product_qty": 1.0,
            }
        )
        return order, line

    def test_product_costs_readonly_by_group(self):
        tmpl = self.product.product_tmpl_id
        self.assertTrue(tmpl.with_user(self.user_read).pba_costs_readonly)
        self.assertTrue(tmpl.with_user(self.user_rfq).pba_costs_readonly)
        self.assertFalse(tmpl.with_user(self.user_all).pba_costs_readonly)

    def test_read_user_cannot_write_product_costs(self):
        tmpl = self.product.product_tmpl_id.with_user(self.user_read)
        with self.assertRaises(AccessError):
            tmpl.write({"pba_cost_freight_percent": 0.2})

    def test_rfq_user_cannot_write_product_costs(self):
        tmpl = self.product.product_tmpl_id.with_user(self.user_rfq)
        with self.assertRaises(AccessError):
            tmpl.write({"pba_cost_freight_percent": 0.2})

    def test_edit_all_user_can_write_product_costs(self):
        tmpl = self.product.product_tmpl_id.with_user(self.user_all)
        tmpl.write({"pba_cost_freight_percent": 0.2})
        self.assertAlmostEqual(tmpl.pba_cost_freight_percent, 0.2)

    def test_read_user_cannot_write_rfq_costs(self):
        _order, line = self._create_rfq()
        with self.assertRaises(AccessError):
            line.with_user(self.user_read).write({"pba_cost_freight_percent": 0.25})

    def test_rfq_user_can_write_costs_before_confirm(self):
        order, line = self._create_rfq()
        self.assertFalse(order.with_user(self.user_rfq).pba_costs_readonly)
        line.with_user(self.user_rfq).write({"pba_cost_freight_percent": 0.25})
        self.assertAlmostEqual(line.pba_cost_freight_percent, 0.25)

    def test_rfq_user_cannot_write_costs_after_confirm(self):
        order, line = self._create_rfq()
        line.write({"pba_cost_freight_percent": 0.25})
        order.with_user(self.user_rfq).button_confirm()
        self.assertIn(order.state, ("purchase", "done"))
        self.assertTrue(order.with_user(self.user_rfq).pba_costs_readonly)
        with self.assertRaises(AccessError):
            line.with_user(self.user_rfq).write({"pba_cost_freight_percent": 0.4})

    def test_rfq_confirm_applies_costs_to_product(self):
        order, line = self._create_rfq()
        line.with_user(self.user_rfq).write({"pba_cost_freight_percent": 0.25})
        order.with_user(self.user_rfq).button_confirm()
        self.assertAlmostEqual(
            self.product.product_tmpl_id.pba_cost_freight_percent,
            0.25,
        )

    def test_edit_all_user_can_write_purchase_costs(self):
        _order, line = self._create_rfq()
        line.with_user(self.user_all).write({"pba_cost_freight_percent": 0.3})
        self.assertAlmostEqual(line.pba_cost_freight_percent, 0.3)
