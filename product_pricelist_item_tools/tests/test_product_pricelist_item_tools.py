from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProductPricelistItemTools(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.pricelist = cls.env["product.pricelist"].create({"name": "Tools Test Pricelist"})
        cls.product_a = cls.env["product.product"].create(
            {"name": "Tools Product A", "list_price": 100.0, "type": "consu"}
        )
        cls.product_b = cls.env["product.product"].create(
            {"name": "Tools Product B", "list_price": 200.0, "type": "consu"}
        )

    def test_duplicate_product_template_forbidden(self):
        self.env["product.pricelist.item"].create(
            {
                "pricelist_id": self.pricelist.id,
                "applied_on": "1_product",
                "product_tmpl_id": self.product_a.product_tmpl_id.id,
                "compute_price": "percentage",
                "percent_price": 10.0,
            }
        )
        with self.assertRaises(ValidationError):
            self.env["product.pricelist.item"].create(
                {
                    "pricelist_id": self.pricelist.id,
                    "applied_on": "1_product",
                    "product_tmpl_id": self.product_a.product_tmpl_id.id,
                    "compute_price": "percentage",
                    "percent_price": 20.0,
                }
            )

    def test_duplicate_product_variant_forbidden(self):
        self.env["product.pricelist.item"].create(
            {
                "pricelist_id": self.pricelist.id,
                "applied_on": "0_product_variant",
                "product_id": self.product_a.id,
                "product_tmpl_id": self.product_a.product_tmpl_id.id,
                "compute_price": "formula",
                "price_discount": 5.0,
            }
        )
        with self.assertRaises(ValidationError):
            self.env["product.pricelist.item"].create(
                {
                    "pricelist_id": self.pricelist.id,
                    "applied_on": "0_product_variant",
                    "product_id": self.product_a.id,
                    "product_tmpl_id": self.product_a.product_tmpl_id.id,
                    "compute_price": "fixed",
                    "fixed_price": 50.0,
                }
            )

    def test_different_products_allowed(self):
        self.env["product.pricelist.item"].create(
            [
                {
                    "pricelist_id": self.pricelist.id,
                    "applied_on": "1_product",
                    "product_tmpl_id": self.product_a.product_tmpl_id.id,
                    "compute_price": "percentage",
                    "percent_price": 10.0,
                },
                {
                    "pricelist_id": self.pricelist.id,
                    "applied_on": "1_product",
                    "product_tmpl_id": self.product_b.product_tmpl_id.id,
                    "compute_price": "percentage",
                    "percent_price": 15.0,
                },
            ]
        )
        self.assertEqual(
            self.env["product.pricelist.item"].search_count(
                [("pricelist_id", "=", self.pricelist.id)]
            ),
            2,
        )

    def test_mass_update_discount(self):
        percentage_item, formula_item, fixed_item = self.env["product.pricelist.item"].create(
            [
                {
                    "pricelist_id": self.pricelist.id,
                    "applied_on": "1_product",
                    "product_tmpl_id": self.product_a.product_tmpl_id.id,
                    "compute_price": "percentage",
                    "percent_price": 10.0,
                },
                {
                    "pricelist_id": self.pricelist.id,
                    "applied_on": "1_product",
                    "product_tmpl_id": self.product_b.product_tmpl_id.id,
                    "compute_price": "formula",
                    "base": "list_price",
                    "price_discount": 5.0,
                },
                {
                    "pricelist_id": self.pricelist.id,
                    "applied_on": "3_global",
                    "compute_price": "fixed",
                    "fixed_price": 1.0,
                },
            ]
        )
        wizard = self.env["product.pricelist.item.discount.wizard"].create(
            {
                "discount": 25.0,
                "item_ids": [
                    Command.set([percentage_item.id, formula_item.id, fixed_item.id])
                ],
            }
        )
        wizard.action_apply_discount()
        self.assertAlmostEqual(percentage_item.percent_price, 25.0)
        self.assertAlmostEqual(formula_item.price_discount, 25.0)
        self.assertAlmostEqual(fixed_item.fixed_price, 1.0)

    def test_mass_update_only_fixed_raises(self):
        fixed_item = self.env["product.pricelist.item"].create(
            {
                "pricelist_id": self.pricelist.id,
                "applied_on": "3_global",
                "compute_price": "fixed",
                "fixed_price": 9.0,
            }
        )
        wizard = self.env["product.pricelist.item.discount.wizard"].create(
            {
                "discount": 12.0,
                "item_ids": [Command.set([fixed_item.id])],
            }
        )
        with self.assertRaises(UserError):
            wizard.action_apply_discount()
