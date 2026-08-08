from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged("post_install", "-at_install")
class TestSaleOrderPosCurrency(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.pos_currency = cls.company.currency_id
        cls.usd = cls.env.ref("base.USD")
        if cls.pos_currency == cls.usd:
            raise AssertionError(
                "Company currency is USD; tests need a distinct POS currency"
            )

        cls.env["res.currency.rate"].search(
            [
                ("currency_id", "=", cls.usd.id),
                ("name", "=", fields.Date.today()),
                ("company_id", "in", [False, cls.company.id]),
            ]
        ).unlink()
        cls.env["res.currency.rate"].create(
            {
                "currency_id": cls.usd.id,
                "company_id": cls.company.id,
                "name": fields.Date.today(),
                "rate": 0.0013564249304933956,
            }
        )

        cls.usd_pricelist = cls.env["product.pricelist"].create(
            {
                "name": "USD Pricelist Test",
                "currency_id": cls.usd.id,
                "company_id": cls.company.id,
            }
        )
        cls.partner = cls.env["res.partner"].create({"name": "POS Currency Partner"})
        sale_tax = cls.env["account.tax"].search(
            [
                ("type_tax_use", "=", "sale"),
                ("company_id", "=", cls.company.id),
                ("amount_type", "=", "percent"),
            ],
            limit=1,
        )
        if not sale_tax:
            sale_tax = cls.env["account.tax"].create(
                {
                    "name": "PBA POS Sale Tax Test",
                    "amount": 16.0,
                    "amount_type": "percent",
                    "type_tax_use": "sale",
                    "company_id": cls.company.id,
                }
            )
        cls.product = cls.env["product.product"].create(
            {
                "name": "POS Currency Product",
                "list_price": 100.0,
                "available_in_pos": True,
                "taxes_id": [(6, 0, [sale_tax.id])],
            }
        )

    def _create_usd_quotation(self, price_unit=100.0):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "pricelist_id": self.usd_pricelist.id,
            }
        )
        line = self.env["sale.order.line"].create(
            {
                "order_id": order.id,
                "product_id": self.product.id,
                "product_uom_qty": 1.0,
                "price_unit": price_unit,
                "technical_price_unit": 0.0,
                "tax_id": [(5, 0, 0)],
            }
        )
        self.assertEqual(order.currency_id, self.usd)
        self.assertEqual(line.price_unit, price_unit)
        return order, line

    def test_pba_pos_convert_price_usd_to_pos_currency(self):
        converted = self.env["sale.order"]._pba_pos_convert_price(
            100.0,
            self.usd,
            self.pos_currency,
            self.company,
        )
        expected = self.usd._convert(
            100.0, self.pos_currency, self.company, fields.Date.today()
        )
        self.assertAlmostEqual(converted, expected, places=2)
        self.assertNotAlmostEqual(converted, 100.0, places=2)

    def test_pba_pos_convert_price_pos_currency_to_usd(self):
        pos_amount = self.usd._convert(
            100.0, self.pos_currency, self.company, fields.Date.today()
        )
        converted = self.env["sale.order"]._pba_pos_convert_price(
            pos_amount,
            self.pos_currency,
            self.usd,
            self.company,
        )
        self.assertAlmostEqual(converted, 100.0, places=2)

    def test_read_converted_applies_pos_currency_context(self):
        _order, line = self._create_usd_quotation(125.33)
        raw = line.read_converted()
        self.assertEqual(len(raw), 1)
        self.assertAlmostEqual(raw[0]["price_unit"], 125.33, places=2)

        converted = line.with_context(
            pba_pos_currency_id=self.pos_currency.id
        ).read_converted()
        self.assertEqual(len(converted), 1)
        expected = self.usd._convert(
            125.33, self.pos_currency, self.company, fields.Date.today()
        )
        self.assertAlmostEqual(converted[0]["price_unit"], expected, places=2)
        self.assertNotAlmostEqual(converted[0]["price_unit"], 125.33, places=2)

    def test_pba_read_prices_in_pos_currency(self):
        _order, line = self._create_usd_quotation(50.0)
        prices = self.env["sale.order.line"].pba_read_prices_in_pos_currency(
            [line.id],
            self.pos_currency.id,
        )
        expected = self.usd._convert(
            50.0, self.pos_currency, self.company, fields.Date.today()
        )
        self.assertIn(line.id, prices)
        self.assertAlmostEqual(prices[line.id], expected, places=2)
        self.assertNotAlmostEqual(prices[line.id], 50.0, places=2)

    def test_pba_has_valued_move_ids_map_batches_lines(self):
        _order, line = self._create_usd_quotation(10.0)
        result = self.env["sale.order.line"].pba_has_valued_move_ids_map([line.id])
        self.assertIn(line.id, result)
        self.assertIsInstance(result[line.id], bool)

    def test_create_quotation_from_pos_converts_pos_currency_to_usd(self):
        pos_unit_price = self.usd._convert(
            10.0, self.pos_currency, self.company, fields.Date.today()
        )
        result = self.env["sale.order"].create_quotation_from_pos(
            {
                "partner_id": self.partner.id,
                "company_id": self.company.id,
                "pricelist_id": self.usd_pricelist.id,
                "pos_currency_id": self.pos_currency.id,
                "lines": [
                    {
                        "product_id": self.product.id,
                        "qty": 1.0,
                        "price_unit": pos_unit_price,
                        "discount": 0.0,
                        "tax_ids": [],
                    }
                ],
            }
        )
        order = self.env["sale.order"].browse(result["id"])
        self.assertEqual(order.currency_id, self.usd)
        self.assertAlmostEqual(order.order_line[0].price_unit, 10.0, places=2)

    def test_create_quotation_from_pos_keeps_invoice_journal(self):
        if "journal_id" not in self.env["sale.order"]._fields:
            self.skipTest("sale.order.journal_id not available")
        journal = self.env["account.journal"].search(
            [("company_id", "=", self.company.id), ("type", "=", "sale")],
            limit=1,
        )
        if not journal:
            self.skipTest("No sale journal available")
        result = self.env["sale.order"].create_quotation_from_pos(
            {
                "partner_id": self.partner.id,
                "company_id": self.company.id,
                "pricelist_id": self.usd_pricelist.id,
                "pos_currency_id": self.pos_currency.id,
                "invoice_journal_id": journal.id,
                "lines": [
                    {
                        "product_id": self.product.id,
                        "qty": 1.0,
                        "price_unit": 10.0,
                        "discount": 0.0,
                        "tax_ids": [],
                    }
                ],
            }
        )
        order = self.env["sale.order"].browse(result["id"])
        self.assertEqual(order.journal_id, journal)

    def test_load_pos_data_fields_includes_currency(self):
        config = self.env["pos.config"].search([], limit=1)
        if not config:
            self.skipTest("No pos.config available")
        fields_list = self.env["sale.order"]._load_pos_data_fields(config.id)
        self.assertIn("currency_id", fields_list)
