from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProductCatalogPricelist(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company_currency = cls.company.currency_id
        cls.foreign_currency = cls.env.ref("base.EUR")
        if cls.foreign_currency == cls.company_currency:
            cls.foreign_currency = cls.env.ref("base.USD")
        cls.env["res.currency.rate"].search(
            [
                ("currency_id", "=", cls.foreign_currency.id),
                ("company_id", "in", [cls.company.id, False]),
            ]
        ).unlink()
        cls.env["res.currency.rate"].create(
            {
                "name": fields.Date.today(),
                "rate": 2.0,
                "currency_id": cls.foreign_currency.id,
                "company_id": cls.company.id,
            }
        )
        cls.product = cls.env["product.product"].create(
            {
                "name": "Catalog Pricelist Product",
                "list_price": 100.0,
                "type": "consu",
            }
        )
        cls.pricelist_company = cls.env["product.pricelist"].create(
            {
                "name": "Company Currency List",
                "currency_id": cls.company_currency.id,
            }
        )
        cls.pricelist_foreign = cls.env["product.pricelist"].create(
            {
                "name": "Foreign Currency List",
                "currency_id": cls.foreign_currency.id,
            }
        )
        cls.order = cls.env["sale.order"].create(
            {
                "partner_id": cls.env.ref("base.res_partner_1").id,
            }
        )

    def _pricelist_data(self, pricelist):
        res = self.order._get_product_catalog_order_data(self.product)
        return next(
            item
            for item in res[self.product.id]["pricelists"]
            if item["id"] == pricelist.id
        )

    def test_new_pricelist_shows_company_currency_by_default(self):
        self.assertTrue(self.pricelist_foreign.catalog_show_company_currency)
        data = self._pricelist_data(self.pricelist_foreign)
        self.assertTrue(data["show_company_currency"])
        self.assertNotEqual(data["currency_id"], data["company_currency_id"])
        self.assertIn("company_currency_price", data)

    def test_hide_company_currency_amount_for_foreign_pricelist(self):
        self.pricelist_foreign.catalog_show_company_currency = False
        data = self._pricelist_data(self.pricelist_foreign)
        self.assertFalse(data["show_company_currency"])

    def test_company_currency_pricelist_keeps_company_amount(self):
        self.pricelist_company.catalog_show_company_currency = False
        data = self._pricelist_data(self.pricelist_company)
        self.assertFalse(data["show_company_currency"])
        self.assertEqual(data["currency_id"], data["company_currency_id"])
