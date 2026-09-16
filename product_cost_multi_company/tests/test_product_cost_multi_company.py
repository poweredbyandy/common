from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProductCostMultiCompany(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env["res.company"].create(
            {
                "name": "Cost Share Company B",
                "currency_id": cls.company_a.currency_id.id,
            }
        )
        cls.other_currency = cls.env.ref("base.EUR")
        if cls.other_currency == cls.company_a.currency_id:
            cls.other_currency = cls.env.ref("base.USD")
        cls.other_currency.active = True
        cls.company_c = cls.env["res.company"].create(
            {
                "name": "Cost Share Company C",
                "currency_id": cls.other_currency.id,
            }
        )
        cls.env["res.currency.rate"].search(
            [
                ("currency_id", "=", cls.company_a.currency_id.id),
                ("company_id", "=", cls.company_c.id),
            ]
        ).unlink()
        cls.env["res.currency.rate"].create(
            {
                "name": fields.Date.today(),
                "currency_id": cls.company_a.currency_id.id,
                "rate": 2.0,
                "company_id": cls.company_c.id,
            }
        )

    def _cost(self, product, company):
        return product.with_company(company).standard_price

    def test_create_without_company_shares_cost(self):
        product = self.env["product.product"].create(
            {
                "name": "Shared cost product",
                "standard_price": 25.0,
                "company_id": False,
            }
        )
        self.assertFalse(product.company_id)
        self.assertAlmostEqual(self._cost(product, self.company_a), 25.0)
        self.assertAlmostEqual(self._cost(product, self.company_b), 25.0)

    def test_write_without_company_shares_cost(self):
        product = self.env["product.product"].create(
            {
                "name": "Shared cost write",
                "standard_price": 10.0,
                "company_id": False,
            }
        )
        product.write({"standard_price": 40.0})
        self.assertAlmostEqual(self._cost(product, self.company_a), 40.0)
        self.assertAlmostEqual(self._cost(product, self.company_b), 40.0)

    def test_product_with_company_keeps_cost_local(self):
        product = self.env["product.product"].create(
            {
                "name": "Company cost product",
                "standard_price": 15.0,
                "company_id": self.company_a.id,
            }
        )
        product.write({"standard_price": 55.0})
        self.assertAlmostEqual(self._cost(product, self.company_a), 55.0)
        self.assertAlmostEqual(self._cost(product, self.company_b), 0.0)

    def test_clearing_company_shares_current_cost(self):
        product = self.env["product.product"].create(
            {
                "name": "Become shared",
                "standard_price": 18.0,
                "company_id": self.company_a.id,
            }
        )
        self.assertAlmostEqual(self._cost(product, self.company_b), 0.0)
        product.write({"company_id": False})
        self.assertFalse(product.company_id)
        self.assertAlmostEqual(self._cost(product, self.company_a), 18.0)
        self.assertAlmostEqual(self._cost(product, self.company_b), 18.0)

    def test_shared_cost_converts_company_currency(self):
        product = (
            self.env["product.product"]
            .with_company(self.company_a)
            .create(
                {
                    "name": "Shared converted cost",
                    "standard_price": 10.0,
                    "company_id": False,
                }
            )
        )
        expected = product._product_cost_share_convert(
            10.0,
            self.company_a,
            self.company_c,
        )
        self.assertNotEqual(expected, 10.0)
        self.assertAlmostEqual(self._cost(product, self.company_c), expected)

    def test_server_action_replicates_from_current_company(self):
        product = self.env["product.product"].create(
            {
                "name": "Manual share action",
                "standard_price": 10.0,
                "company_id": False,
            }
        )
        product.with_company(self.company_b).with_context(
            skip_product_cost_multi_company=True,
        ).write({"standard_price": 99.0})
        self.assertAlmostEqual(self._cost(product, self.company_a), 10.0)
        self.assertAlmostEqual(self._cost(product, self.company_b), 99.0)
        action = self.env.ref(
            "product_cost_multi_company.product_product_action_share_standard_price"
        )
        action.with_company(self.company_b).with_context(
            active_model="product.product",
            active_id=product.id,
            active_ids=product.ids,
        ).run()
        self.assertAlmostEqual(self._cost(product, self.company_a), 99.0)
        self.assertAlmostEqual(self._cost(product, self.company_b), 99.0)

    def test_server_action_requires_no_company(self):
        product = self.env["product.product"].create(
            {
                "name": "Local company product",
                "standard_price": 10.0,
                "company_id": self.company_a.id,
            }
        )
        with self.assertRaises(UserError):
            product.action_share_standard_price_across_companies()
