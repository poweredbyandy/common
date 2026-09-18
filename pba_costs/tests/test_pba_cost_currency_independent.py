from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPbaCostCurrencyIndependent(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_currency = cls.env.company.currency_id
        cls.other_currency = cls.env.ref("base.EUR")
        if cls.other_currency == cls.company_currency:
            cls.other_currency = cls.env.ref("base.USD")
        cls.other_currency.active = True
        cls.env["res.currency.rate"].search(
            [
                ("currency_id", "=", cls.other_currency.id),
                ("company_id", "=", cls.env.company.id),
            ]
        ).unlink()
        cls.env["res.currency.rate"].create(
            {
                "name": fields.Date.today(),
                "currency_id": cls.other_currency.id,
                "rate": 2.0,
                "company_id": cls.env.company.id,
            }
        )

    def test_pba_cost_currency_independent_from_product_cost(self):
        template = self.env["product.template"].create(
            {
                "name": "PBA own cost currency",
                "list_price": 100.0,
                "standard_price": 40.0,
                "pba_force_cost_currency_id": self.other_currency.id,
                "pba_cost_freight_percent": 0.1,
            }
        )
        self.assertEqual(template.pba_cost_currency_id, self.other_currency)
        self.assertEqual(template.cost_currency_id, self.company_currency)
        self.assertEqual(template.currency_id, self.company_currency)

    def test_product_cost_currency_change_does_not_change_pba(self):
        Template = self.env["product.template"]
        if "force_cost_currency_id" not in Template._fields:
            self.skipTest("l10n_ve_product_currency is not installed")
        template = Template.create(
            {
                "name": "PBA keeps own currency",
                "list_price": 100.0,
                "standard_price": 40.0,
                "force_cost_currency_id": self.company_currency.id,
                "pba_force_cost_currency_id": self.other_currency.id,
                "pba_cost_freight_percent": 0.1,
            }
        )
        self.assertEqual(template.pba_cost_currency_id, self.other_currency)
        third_currency = self.env.ref("base.USD")
        if third_currency in (self.company_currency, self.other_currency):
            third_currency = self.env.ref("base.GBP")
        third_currency.active = True
        template.write({"force_cost_currency_id": third_currency.id})
        self.assertEqual(template.cost_currency_id, third_currency)
        self.assertEqual(template.pba_cost_currency_id, self.other_currency)
        template.write({"force_cost_currency_id": False})
        self.assertEqual(template.cost_currency_id, self.company_currency)
        self.assertEqual(template.pba_cost_currency_id, self.other_currency)

    def test_sale_currency_change_keeps_pba_cost_currency(self):
        Template = self.env["product.template"]
        if "force_currency_id" not in Template._fields:
            self.skipTest("l10n_ve_product_currency is not installed")
        template = Template.create(
            {
                "name": "PBA keeps cost currency",
                "list_price": 100.0,
                "standard_price": 40.0,
                "force_currency_id": self.company_currency.id,
                "force_cost_currency_id": self.company_currency.id,
                "pba_force_cost_currency_id": self.other_currency.id,
                "pba_cost_freight_percent": 0.1,
            }
        )
        self.assertEqual(template.pba_cost_currency_id, self.other_currency)
        template.write({"force_currency_id": self.other_currency.id})
        self.assertEqual(template.pba_cost_currency_id, self.other_currency)
        self.assertEqual(template.cost_currency_id, self.company_currency)
        self.assertEqual(template.currency_id, self.other_currency)
        self.assertAlmostEqual(template.standard_price, 40.0, places=4)
