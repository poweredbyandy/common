from odoo.tests import Form, TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPbaUtilityFromSalePrice(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.user.groups_id += (
            cls.env.ref("pba_costs.group_pba_product_costs_tab")
            | cls.env.ref("pba_costs.group_pba_costs_edit_all")
        )
        cls.partner = cls.env["res.partner"].create({"name": "PBA Utility Vendor"})
        cls.template = cls.env["product.template"].create(
            {
                "name": "PBA Utility Product",
                "list_price": 100.0,
                "standard_price": 100.0,
                "purchase_ok": True,
                "sale_ok": True,
                "pba_cost_freight_percent": 0.1,
                "pba_utility_percent": 0.2,
            }
        )
        cls.product = cls.template.product_variant_id

    def test_suggested_price_follows_utility_percent(self):
        self.assertAlmostEqual(self.template.pba_final_cost, 110.0)
        self.assertAlmostEqual(self.template.pba_suggested_list_price, 132.0)
        self.assertAlmostEqual(self.template.pba_utility_margin_amount, 22.0)

    def test_purchase_line_sale_price_write_recomputes_utility(self):
        order = self.env["purchase.order"].create({"partner_id": self.partner.id})
        line = self.env["purchase.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "product_qty": 1.0,
                "price_unit": 80.0,
                "pba_utility_percent": 0.25,
            }
        )
        self.assertAlmostEqual(line.pba_projected_final_cost, 88.0)
        self.assertAlmostEqual(line.pba_sale_price_suggested, 110.0)
        line.write({"pba_sale_price_unit": 132.0})
        self.assertAlmostEqual(line.pba_utility_percent, 0.5)
        self.assertAlmostEqual(line.pba_utility_margin_amount, 44.0)
        self.assertAlmostEqual(line.pba_sale_price_suggested, 132.0)

    def test_purchase_line_create_with_sale_price_recomputes_utility(self):
        order = self.env["purchase.order"].create({"partner_id": self.partner.id})
        line = self.env["purchase.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "product_qty": 1.0,
                "price_unit": 80.0,
                "pba_sale_price_unit": 132.0,
            }
        )
        self.assertAlmostEqual(line.pba_projected_final_cost, 88.0)
        self.assertAlmostEqual(line.pba_utility_percent, 0.5)

    def test_purchase_line_write_keeps_explicit_utility(self):
        order = self.env["purchase.order"].create({"partner_id": self.partner.id})
        line = self.env["purchase.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "product_qty": 1.0,
                "price_unit": 80.0,
                "pba_utility_percent": 0.25,
            }
        )
        line.write(
            {
                "pba_utility_percent": 0.3,
                "pba_sale_price_unit": 999.0,
            }
        )
        self.assertAlmostEqual(line.pba_utility_percent, 0.3)

    def test_purchase_line_form_sale_price_onchange_recomputes_utility(self):
        order_form = Form(self.env["purchase.order"])
        order_form.partner_id = self.partner
        with order_form.order_line.new() as line_form:
            line_form.product_id = self.product
            line_form.product_qty = 1.0
            line_form.price_unit = 80.0
            line_form.pba_utility_percent = 0.25
            self.assertAlmostEqual(line_form.pba_projected_final_cost, 88.0)
            line_form.pba_sale_price_unit = 132.0
            self.assertAlmostEqual(line_form.pba_utility_percent, 0.5)
            self.assertAlmostEqual(line_form.pba_sale_price_unit, 132.0)

    def test_update_list_price_from_suggested(self):
        self.assertAlmostEqual(self.template.list_price, 100.0)
        self.assertAlmostEqual(self.template.pba_suggested_list_price, 132.0)
        action = self.template.action_pba_update_list_price()
        self.assertAlmostEqual(self.template.list_price, 132.0)
        self.assertEqual(action["tag"], "display_notification")

    def test_update_list_price_from_variant(self):
        self.product.action_pba_update_list_price()
        self.assertAlmostEqual(self.template.list_price, 132.0)

