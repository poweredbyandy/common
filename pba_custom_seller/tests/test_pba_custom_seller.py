from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestPbaCustomSeller(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.custom_seller_group = cls.env.ref("pba_custom_seller.group_pba_custom_seller")
        cls.see_qty_group = cls.env.ref("pba_custom_seller.group_pba_custom_seller_see_qty")
        # Isolate from staging/public pricelists visible to the same groups.
        cls.env["product.pricelist"].search([]).write({"active": False})

        cls.user_seller = new_test_user(
            cls.env,
            login="pba_custom_seller_user",
            groups="base.group_user,pba_custom_seller.group_pba_custom_seller",
        )
        cls.user_seller_qty = new_test_user(
            cls.env,
            login="pba_custom_seller_qty_user",
            groups="base.group_user,pba_custom_seller.group_pba_custom_seller_see_qty",
        )

        cls.product_in = cls.env["product.product"].create(
            {"name": "Seller Visible Product", "list_price": 10.0, "type": "consu", "is_storable": True}
        )
        cls.product_out = cls.env["product.product"].create(
            {"name": "Seller Hidden Product", "list_price": 20.0, "type": "consu", "is_storable": True}
        )
        cls.pricelist = cls.env["product.pricelist"].create(
            {
                "name": "Seller Pricelist",
                "group_ids": [Command.set([cls.custom_seller_group.id])],
                "item_ids": [
                    Command.create(
                        {
                            "applied_on": "1_product",
                            "product_tmpl_id": cls.product_in.product_tmpl_id.id,
                            "compute_price": "fixed",
                            "fixed_price": 10.0,
                        }
                    )
                ],
            }
        )
        cls.partner_own = cls.env["res.partner"].create(
            {"name": "Own Customer", "user_id": cls.user_seller.id}
        )
        cls.partner_other = cls.env["res.partner"].create(
            {"name": "Other Customer", "user_id": cls.user_seller_qty.id}
        )

    def test_partner_own_only(self):
        partners = (
            self.env["res.partner"]
            .with_user(self.user_seller)
            .search([("id", "in", [self.partner_own.id, self.partner_other.id])])
        )
        self.assertEqual(partners, self.partner_own)

    def test_partner_visible_when_assigned_on_sale_order(self):
        self.env["sale.order"].create(
            {
                "partner_id": self.partner_other.id,
                "user_id": self.user_seller.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.product_in.id,
                            "product_uom_qty": 1.0,
                        }
                    )
                ],
            }
        )
        partners = (
            self.env["res.partner"]
            .with_user(self.user_seller)
            .search([("id", "in", [self.partner_own.id, self.partner_other.id])])
        )
        self.assertEqual(
            set(partners.ids), {self.partner_own.id, self.partner_other.id}
        )

    def test_internal_user_partners_visible(self):
        partners = (
            self.env["res.partner"]
            .with_user(self.user_seller)
            .search([("id", "=", self.user_seller_qty.partner_id.id)])
        )
        self.assertEqual(partners, self.user_seller_qty.partner_id)

    def test_products_limited_to_pricelist_items(self):
        products = (
            self.env["product.product"]
            .with_user(self.user_seller)
            .search([("id", "in", [self.product_in.id, self.product_out.id])])
        )
        self.assertEqual(products, self.product_in)

    def test_products_ignore_other_group_pricelists_via_env_user(self):
        """env.user is sudoed; foreign pricelists must still be excluded."""
        other_group = self.env["res.groups"].create({"name": "PBA Other Pricelist Group"})
        self.env["product.pricelist"].create(
            {
                "name": "Other Group Pricelist",
                "group_ids": [Command.set([other_group.id])],
                "item_ids": [
                    Command.create(
                        {
                            "applied_on": "1_product",
                            "product_tmpl_id": self.product_out.product_tmpl_id.id,
                            "compute_price": "fixed",
                            "fixed_price": 20.0,
                        }
                    )
                ],
            }
        )
        products = (
            self.env["product.product"]
            .with_user(self.user_seller)
            .search([("id", "in", [self.product_in.id, self.product_out.id])])
        )
        self.assertEqual(products, self.product_in)
        # env.user is always sudoed; allowed products must still respect ir.rules
        allowed = self.env(user=self.user_seller).user._pba_custom_seller_allowed_products()
        self.assertIn(self.product_in, allowed)
        self.assertNotIn(self.product_out, allowed)

    def test_specific_items_win_over_global_rule(self):
        self.env["product.pricelist.item"].create(
            {
                "pricelist_id": self.pricelist.id,
                "applied_on": "3_global",
                "compute_price": "formula",
                "price_discount": 0.0,
            }
        )
        products = (
            self.env["product.product"]
            .with_user(self.user_seller)
            .search([("id", "in", [self.product_in.id, self.product_out.id])])
        )
        self.assertEqual(products, self.product_in)

    def test_only_global_pricelist_shows_all_products(self):
        self.pricelist.item_ids.unlink()
        self.env["product.pricelist.item"].create(
            {
                "pricelist_id": self.pricelist.id,
                "applied_on": "3_global",
                "compute_price": "formula",
                "price_discount": 0.0,
            }
        )
        products = (
            self.env["product.product"]
            .with_user(self.user_seller)
            .search([("id", "in", [self.product_in.id, self.product_out.id])])
        )
        self.assertEqual(set(products.ids), {self.product_in.id, self.product_out.id})

    def test_hide_zero_price_products_group(self):
        product_zero = self.env["product.product"].create(
            {
                "name": "Seller Zero Price Product",
                "list_price": 30.0,
                "type": "consu",
            }
        )
        self.env["product.pricelist.item"].create(
            {
                "pricelist_id": self.pricelist.id,
                "applied_on": "1_product",
                "product_tmpl_id": product_zero.product_tmpl_id.id,
                "compute_price": "fixed",
                "fixed_price": 0.0,
            }
        )
        user_hide_zero = new_test_user(
            self.env,
            login="pba_custom_seller_hide_zero",
            groups="base.group_user,pba_custom_seller.group_pba_custom_seller_hide_zero",
        )
        products = (
            self.env["product.product"]
            .with_user(user_hide_zero)
            .search(
                [
                    (
                        "id",
                        "in",
                        [self.product_in.id, self.product_out.id, product_zero.id],
                    )
                ]
            )
        )
        self.assertEqual(products, self.product_in)

    def test_stock_qty_hidden_without_group(self):
        self.product_in.with_user(self.env.ref("base.user_admin")).write({})
        product = self.product_in.with_user(self.user_seller)
        product.invalidate_recordset(["qty_available", "free_qty", "virtual_available"])
        self.assertEqual(product.qty_available, 0.0)
        self.assertEqual(product.free_qty, 0.0)

    def test_stock_qty_visible_with_group(self):
        self.assertTrue(
            self.user_seller_qty.has_group(
                "pba_custom_seller.group_pba_custom_seller_see_qty"
            )
        )
        self.assertTrue(self.user_seller_qty._pba_can_see_stock_qty())

    def test_cannot_confirm_without_confirm_group(self):
        self.assertFalse(self.user_seller._pba_can_confirm_sale_order())
        order = (
            self.env["sale.order"]
            .with_user(self.user_seller)
            .create(
                {
                    "partner_id": self.partner_own.id,
                    "user_id": self.user_seller.id,
                    "order_line": [
                        Command.create(
                            {
                                "product_id": self.product_in.id,
                                "product_uom_qty": 1.0,
                            }
                        )
                    ],
                }
            )
        )
        with self.assertRaises(UserError):
            order.action_confirm()
