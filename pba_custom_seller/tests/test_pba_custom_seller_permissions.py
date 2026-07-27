from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestPbaCustomSellerPermissions(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.custom_seller_group = cls.env.ref("pba_custom_seller.group_pba_custom_seller")
        cls.see_qty_group = cls.env.ref("pba_custom_seller.group_pba_custom_seller_see_qty")
        cls.confirm_group = cls.env.ref("pba_custom_seller.group_pba_custom_seller_confirm_so")
        cls.see_all_pricelists = cls.env.ref(
            "product_pricelist_group.group_product_pricelist_all"
        )

        cls.user_salesman = new_test_user(
            cls.env,
            login="pba_std_salesman",
            groups=(
                "base.group_user,"
                "sales_team.group_sale_salesman,"
                "product.group_product_pricelist,"
                "stock.group_stock_user"
            ),
        )
        cls.user_custom = new_test_user(
            cls.env,
            login="pba_custom_seller_limited",
            groups="base.group_user,pba_custom_seller.group_pba_custom_seller,stock.group_stock_user",
        )
        cls.user_custom_confirm = new_test_user(
            cls.env,
            login="pba_custom_seller_confirm",
            groups=(
                "base.group_user,"
                "pba_custom_seller.group_pba_custom_seller_confirm_so,"
                "stock.group_stock_user"
            ),
        )
        cls.user_custom_qty = new_test_user(
            cls.env,
            login="pba_custom_seller_with_qty",
            groups=(
                "base.group_user,"
                "pba_custom_seller.group_pba_custom_seller_see_qty,"
                "stock.group_stock_user"
            ),
        )

        cls.product_in = cls.env["product.product"].create(
            {
                "name": "PBA Product In Pricelist",
                "list_price": 10.0,
                "type": "consu",
                "is_storable": True,
            }
        )
        cls.product_out = cls.env["product.product"].create(
            {
                "name": "PBA Product Outside Pricelist",
                "list_price": 20.0,
                "type": "consu",
                "is_storable": True,
            }
        )
        cls.pricelist_public = cls.env["product.pricelist"].create(
            {"name": "PBA Public Pricelist"}
        )
        cls.pricelist_restricted = cls.env["product.pricelist"].create(
            {
                "name": "PBA Restricted Custom Seller Pricelist",
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
        cls.pricelist_see_all_only = cls.env["product.pricelist"].create(
            {
                "name": "PBA See All Only Pricelist",
                "group_ids": [Command.set([cls.see_all_pricelists.id])],
            }
        )

        cls.partner_custom = cls.env["res.partner"].create(
            {"name": "Customer of Custom Seller", "user_id": cls.user_custom.id}
        )
        cls.partner_salesman = cls.env["res.partner"].create(
            {"name": "Customer of Salesman", "user_id": cls.user_salesman.id}
        )
        cls.partner_custom_confirm = cls.env["res.partner"].create(
            {
                "name": "Customer of Confirm Seller",
                "user_id": cls.user_custom_confirm.id,
            }
        )

        warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.env["stock.quant"].with_context(inventory_mode=True).create(
            {
                "product_id": cls.product_in.id,
                "location_id": warehouse.lot_stock_id.id,
                "inventory_quantity": 25.0,
            }
        ).action_apply_inventory()

    def test_salesman_sees_all_partners(self):
        partners = (
            self.env["res.partner"]
            .with_user(self.user_salesman)
            .search(
                [
                    (
                        "id",
                        "in",
                        [self.partner_custom.id, self.partner_salesman.id],
                    )
                ]
            )
        )
        self.assertEqual(
            set(partners.ids), {self.partner_custom.id, self.partner_salesman.id}
        )

    def test_custom_seller_sees_only_own_partners(self):
        partners = (
            self.env["res.partner"]
            .with_user(self.user_custom)
            .search(
                [
                    (
                        "id",
                        "in",
                        [self.partner_custom.id, self.partner_salesman.id],
                    )
                ]
            )
        )
        self.assertEqual(partners, self.partner_custom)

    def test_salesman_sees_all_products(self):
        products = (
            self.env["product.product"]
            .with_user(self.user_salesman)
            .search([("id", "in", [self.product_in.id, self.product_out.id])])
        )
        self.assertEqual(set(products.ids), {self.product_in.id, self.product_out.id})

    def test_custom_seller_sees_only_pricelist_products(self):
        products = (
            self.env["product.product"]
            .with_user(self.user_custom)
            .search([("id", "in", [self.product_in.id, self.product_out.id])])
        )
        self.assertEqual(products, self.product_in)

    def test_salesman_sees_public_and_not_restricted_without_group(self):
        pricelists = (
            self.env["product.pricelist"]
            .with_user(self.user_salesman)
            .search(
                [
                    (
                        "id",
                        "in",
                        [
                            self.pricelist_public.id,
                            self.pricelist_restricted.id,
                            self.pricelist_see_all_only.id,
                        ],
                    )
                ]
            )
        )
        self.assertIn(self.pricelist_public, pricelists)
        self.assertNotIn(self.pricelist_restricted, pricelists)
        self.assertNotIn(self.pricelist_see_all_only, pricelists)

    def test_custom_seller_sees_restricted_pricelist(self):
        pricelists = (
            self.env["product.pricelist"]
            .with_user(self.user_custom)
            .search(
                [
                    (
                        "id",
                        "in",
                        [
                            self.pricelist_public.id,
                            self.pricelist_restricted.id,
                            self.pricelist_see_all_only.id,
                        ],
                    )
                ]
            )
        )
        self.assertIn(self.pricelist_public, pricelists)
        self.assertIn(self.pricelist_restricted, pricelists)
        self.assertNotIn(self.pricelist_see_all_only, pricelists)

    def test_salesman_can_see_stock_qty(self):
        self.assertTrue(self.user_salesman._pba_can_see_stock_qty())

    def test_custom_seller_cannot_see_stock_qty_by_default(self):
        self.assertFalse(self.user_custom._pba_can_see_stock_qty())
        product = self.product_in.with_user(self.user_custom)
        product.invalidate_recordset(["qty_available", "free_qty"])
        self.assertEqual(product.qty_available, 0.0)
        self.assertEqual(product.free_qty, 0.0)

    def test_custom_seller_with_qty_group_can_see_stock_qty(self):
        self.assertTrue(self.user_custom_qty._pba_can_see_stock_qty())

    def test_salesman_sees_qty_widget_on_sale_line(self):
        order = (
            self.env["sale.order"]
            .with_user(self.user_salesman)
            .create(
                {
                    "partner_id": self.partner_salesman.id,
                    "pricelist_id": self.pricelist_public.id,
                    "user_id": self.user_salesman.id,
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
        line = order.order_line
        self.assertTrue(line.display_qty_widget)
        self.assertGreater(line.free_qty_today, 0.0)

    def test_custom_seller_hides_qty_widget_on_sale_line(self):
        order = (
            self.env["sale.order"]
            .with_user(self.user_custom)
            .create(
                {
                    "partner_id": self.partner_custom.id,
                    "pricelist_id": self.pricelist_restricted.id,
                    "user_id": self.user_custom.id,
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
        line = order.order_line
        self.assertFalse(line.display_qty_widget)
        self.assertEqual(line.free_qty_today, 0.0)
        self.assertEqual(line.qty_available_today, 0.0)
        self.assertEqual(line.virtual_available_at_date, 0.0)

    def test_custom_seller_with_qty_group_sees_qty_widget_on_sale_line(self):
        order = (
            self.env["sale.order"]
            .with_user(self.user_custom_qty)
            .create(
                {
                    "partner_id": self.partner_custom.id,
                    "pricelist_id": self.pricelist_restricted.id,
                    "user_id": self.user_custom_qty.id,
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
        line = order.order_line.with_user(self.user_custom_qty)
        self.assertTrue(line.display_qty_widget)
        self.assertGreater(line.free_qty_today, 0.0)

    def test_salesman_can_confirm_sale_order(self):
        order = (
            self.env["sale.order"]
            .with_user(self.user_salesman)
            .create(
                {
                    "partner_id": self.partner_salesman.id,
                    "pricelist_id": self.pricelist_public.id,
                    "user_id": self.user_salesman.id,
                    "order_line": [
                        Command.create(
                            {
                                "product_id": self.product_out.id,
                                "product_uom_qty": 1.0,
                            }
                        )
                    ],
                }
            )
        )
        order.action_confirm()
        self.assertEqual(order.state, "sale")

    def test_custom_seller_cannot_confirm_without_group(self):
        order = (
            self.env["sale.order"]
            .with_user(self.user_custom)
            .create(
                {
                    "partner_id": self.partner_custom.id,
                    "pricelist_id": self.pricelist_restricted.id,
                    "user_id": self.user_custom.id,
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
        self.assertEqual(order.state, "draft")

    def test_custom_seller_can_confirm_with_group(self):
        order = (
            self.env["sale.order"]
            .with_user(self.user_custom_confirm)
            .create(
                {
                    "partner_id": self.partner_custom_confirm.id,
                    "pricelist_id": self.pricelist_restricted.id,
                    "user_id": self.user_custom_confirm.id,
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
        order.action_confirm()
        self.assertEqual(order.state, "sale")
