from odoo.fields import Command
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestProductPricelistGroup(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.group_a = cls.env["res.groups"].create({"name": "Pricelist Group A"})
        cls.group_b = cls.env["res.groups"].create({"name": "Pricelist Group B"})

        cls.user_a = new_test_user(
            cls.env,
            login="pricelist_user_a",
            groups="base.group_user,product.group_product_pricelist",
        )
        cls.user_a.groups_id = [(4, cls.group_a.id)]

        cls.user_b = new_test_user(
            cls.env,
            login="pricelist_user_b",
            groups="base.group_user,product.group_product_pricelist",
        )
        cls.user_b.groups_id = [(4, cls.group_b.id)]

        cls.user_plain = new_test_user(
            cls.env,
            login="pricelist_user_plain",
            groups="base.group_user,product.group_product_pricelist",
        )

        cls.user_product_manager = new_test_user(
            cls.env,
            login="pricelist_user_product_manager",
            groups="base.group_user,product.group_product_manager,product.group_product_pricelist",
        )

        cls.user_see_all = new_test_user(
            cls.env,
            login="pricelist_user_see_all",
            groups=(
                "base.group_user,product.group_product_pricelist,"
                "product_pricelist_group.group_product_pricelist_all"
            ),
        )

        cls.user_salesman = new_test_user(
            cls.env,
            login="pricelist_user_salesman",
            groups=(
                "base.group_user,product.group_product_pricelist,"
                "sales_team.group_sale_salesman"
            ),
        )

        cls.product = cls.env["product.product"].create(
            {
                "name": "Pricelist Group Test Product",
                "list_price": 100.0,
                "type": "consu",
            }
        )

        cls.pricelist_public = cls.env["product.pricelist"].create(
            {
                "name": "Public Pricelist",
            }
        )
        cls.pricelist_a = cls.env["product.pricelist"].create(
            {
                "name": "Restricted Group A",
                "group_ids": [Command.set([cls.group_a.id])],
            }
        )
        cls.pricelist_b = cls.env["product.pricelist"].create(
            {
                "name": "Restricted Group B",
                "group_ids": [Command.set([cls.group_b.id])],
            }
        )
        cls.pricelist_base = cls.env["product.pricelist"].create(
            {
                "name": "Base Restricted to B",
                "group_ids": [Command.set([cls.group_b.id])],
                "item_ids": [
                    Command.create(
                        {
                            "applied_on": "3_global",
                            "compute_price": "fixed",
                            "fixed_price": 80.0,
                        }
                    )
                ],
            }
        )
        cls.pricelist_dependent = cls.env["product.pricelist"].create(
            {
                "name": "Dependent Visible to A",
                "group_ids": [Command.set([cls.group_a.id])],
                "item_ids": [
                    Command.create(
                        {
                            "applied_on": "3_global",
                            "compute_price": "formula",
                            "base": "pricelist",
                            "base_pricelist_id": cls.pricelist_base.id,
                            "price_discount": 10.0,
                        }
                    )
                ],
            }
        )

    def test_public_pricelist_visible_to_everyone(self):
        for user in (self.user_a, self.user_b, self.user_plain):
            pricelists = (
                self.env["product.pricelist"]
                .with_user(user)
                .search([("id", "=", self.pricelist_public.id)])
            )
            self.assertEqual(pricelists, self.pricelist_public)

    def test_restricted_pricelist_visible_only_to_group(self):
        visible_a = (
            self.env["product.pricelist"]
            .with_user(self.user_a)
            .search([("id", "in", [self.pricelist_a.id, self.pricelist_b.id])])
        )
        self.assertEqual(visible_a, self.pricelist_a)

        visible_b = (
            self.env["product.pricelist"]
            .with_user(self.user_b)
            .search([("id", "in", [self.pricelist_a.id, self.pricelist_b.id])])
        )
        self.assertEqual(visible_b, self.pricelist_b)

        visible_plain = (
            self.env["product.pricelist"]
            .with_user(self.user_plain)
            .search([("id", "in", [self.pricelist_a.id, self.pricelist_b.id])])
        )
        self.assertFalse(visible_plain)

    def test_see_all_group_sees_all_pricelists(self):
        visible = (
            self.env["product.pricelist"]
            .with_user(self.user_see_all)
            .search(
                [
                    (
                        "id",
                        "in",
                        [
                            self.pricelist_public.id,
                            self.pricelist_a.id,
                            self.pricelist_b.id,
                            self.pricelist_base.id,
                            self.pricelist_dependent.id,
                        ],
                    )
                ]
            )
        )
        self.assertEqual(len(visible), 5)

    def test_salesman_does_not_see_all_pricelists(self):
        self.assertFalse(
            self.user_salesman.has_group(
                "product_pricelist_group.group_product_pricelist_all"
            )
        )
        visible = (
            self.env["product.pricelist"]
            .with_user(self.user_salesman)
            .search(
                [
                    (
                        "id",
                        "in",
                        [
                            self.pricelist_public.id,
                            self.pricelist_a.id,
                            self.pricelist_b.id,
                        ],
                    )
                ]
            )
        )
        self.assertEqual(visible, self.pricelist_public)

    def test_product_manager_does_not_bypass_restrictions(self):
        visible = (
            self.env["product.pricelist"]
            .with_user(self.user_product_manager)
            .search(
                [
                    (
                        "id",
                        "in",
                        [
                            self.pricelist_public.id,
                            self.pricelist_a.id,
                            self.pricelist_b.id,
                        ],
                    )
                ]
            )
        )
        self.assertEqual(visible, self.pricelist_public)

    def test_dependent_base_hidden_but_price_computed(self):
        env_a = self.env["product.pricelist"].with_user(self.user_a)
        self.assertFalse(
            env_a.search([("id", "=", self.pricelist_base.id)]),
            "Base pricelist restricted to group B must stay hidden for user A",
        )
        self.assertTrue(
            env_a.search([("id", "=", self.pricelist_dependent.id)]),
            "Dependent pricelist must be visible for user A",
        )

        price = (
            self.pricelist_dependent.with_user(self.user_a)._get_product_price(
                self.product, 1.0
            )
        )
        self.assertAlmostEqual(price, 72.0)

    def test_user_cannot_search_restricted_for_catalog_style_query(self):
        pricelists = (
            self.env["product.pricelist"]
            .with_user(self.user_a)
            .search([("active", "=", True)])
        )
        self.assertIn(self.pricelist_public, pricelists)
        self.assertIn(self.pricelist_a, pricelists)
        self.assertIn(self.pricelist_dependent, pricelists)
        self.assertNotIn(self.pricelist_b, pricelists)
        self.assertNotIn(self.pricelist_base, pricelists)

    def test_inaccessible_pricelist_price_falls_back(self):
        price = self.pricelist_b.with_user(self.user_a)._get_product_price(
            self.product, 1.0
        )
        expected = self.pricelist_public.with_user(self.user_a)._get_product_price(
            self.product, 1.0
        )
        self.assertAlmostEqual(price, expected)

    def test_partner_pricelist_skips_inaccessible(self):
        partner = self.env["res.partner"].create(
            {
                "name": "Partner restricted pricelist",
                "specific_property_product_pricelist": self.pricelist_b.id,
            }
        )
        resolved = (
            self.env["product.pricelist"]
            .with_user(self.user_a)
            ._get_partner_pricelist_multi(partner.ids)
        )
        self.assertNotEqual(resolved[partner.id], self.pricelist_b)
        self.assertTrue(resolved[partner.id]._filtered_access("read"))
