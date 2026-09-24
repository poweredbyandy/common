from odoo.fields import Command
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPbaLastSalePricePricelist(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "PBA Last Sale"})
        cls.template = cls.env["product.template"].create(
            {
                "name": "PBA Last Sale Product",
                "type": "service",
                "list_price": 5.0,
                "sale_ok": True,
            }
        )
        cls.product = cls.template.product_variant_id
        cls.currency = cls.env.company.currency_id

    def _pricelist(self, name, item_vals):
        return self.env["product.pricelist"].create(
            {
                "name": name,
                "currency_id": self.currency.id,
                "item_ids": [
                    Command.create(
                        {
                            "applied_on": "1_product",
                            "product_tmpl_id": self.template.id,
                            **item_vals,
                        }
                    )
                ],
            }
        )

    def _confirm_sale(self, pricelist, **line_vals):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.partner.id,
                "pricelist_id": pricelist.id,
                "order_line": [
                    Command.create(
                        {
                            "product_id": self.product.id,
                            "product_uom_qty": 1.0,
                            **line_vals,
                        }
                    )
                ],
            }
        )
        if line_vals:
            order.order_line.write(line_vals)
        order.action_confirm()
        return order

    def test_formula_markup_returns_catalog_price(self):
        pricelist = self._pricelist(
            "PBA markup 20",
            {
                "compute_price": "formula",
                "base": "list_price",
                "price_discount": -20.0,
            },
        )
        order = self._confirm_sale(pricelist)
        self.assertAlmostEqual(order.order_line.price_unit, 6.0)
        self.assertAlmostEqual(self.template.pba_last_sale_price, 5.0)

    def test_percentage_discount_returns_catalog_price(self):
        self.template.list_price = 10.0
        pricelist = self._pricelist(
            "PBA discount 10",
            {
                "compute_price": "percentage",
                "base": "list_price",
                "percent_price": 10.0,
            },
        )
        order = self._confirm_sale(pricelist)
        self.assertAlmostEqual(self.template.pba_last_sale_price, 10.0)
        self.assertLess(order.order_line.price_unit * (1 - order.order_line.discount / 100.0), 10.0)

    def test_manual_price_inverts_formula(self):
        pricelist = self._pricelist(
            "PBA markup manual",
            {
                "compute_price": "formula",
                "base": "list_price",
                "price_discount": -20.0,
            },
        )
        order = self._confirm_sale(pricelist, price_unit=7.2, discount=0.0)
        self.assertAlmostEqual(order.order_line.price_unit, 7.2)
        self.assertAlmostEqual(self.template.pba_last_sale_price, 6.0)

    def test_fixed_price_returns_catalog_base(self):
        pricelist = self._pricelist(
            "PBA fixed",
            {
                "compute_price": "fixed",
                "fixed_price": 6.0,
            },
        )
        order = self._confirm_sale(pricelist)
        self.assertAlmostEqual(order.order_line.price_unit, 6.0)
        self.assertAlmostEqual(self.template.pba_last_sale_price, 5.0)
