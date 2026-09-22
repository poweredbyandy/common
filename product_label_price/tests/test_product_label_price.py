from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProductLabelPrice(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {
                "name": "Label Price Product",
                "default_code": "LBL-PRICE",
                "barcode": "8412345678001",
                "list_price": 25.0,
            }
        )
        cls.pricelist = cls.env["product.pricelist"].search([], limit=1)
        if not cls.pricelist:
            cls.pricelist = cls.env["product.pricelist"].create(
                {"name": "Label Price"}
            )

    def _render_simple_label(self, xmlid):
        return str(
            self.env["ir.qweb"]._render(
                xmlid,
                {
                    "product": self.product,
                    "barcode": self.product.barcode,
                    "pricelist": self.pricelist,
                    "extra_html": "",
                    "make_invisible": False,
                    "table_style": "",
                },
            )
        )

    def test_company_shows_price_by_default(self):
        self.assertTrue(self.env.company.product_label_show_price)

    def test_pdf_labels_include_price_when_enabled(self):
        self.env.company.product_label_show_price = True
        html_2x7 = self._render_simple_label("product.report_simple_label2x7")
        html_4x7 = self._render_simple_label("product.report_simple_label4x7")
        html_4x12 = self._render_simple_label("product.report_simple_label4x12")
        html_dymo = self._render_simple_label("product.report_simple_label_dymo")
        self.assertIn("o_label_price", html_2x7)
        self.assertIn("o_label_price_medium", html_4x7)
        self.assertIn("o_label_price_medium", html_4x12)
        self.assertIn("o_label_price_small", html_dymo)

    def test_pdf_labels_hide_price_when_disabled(self):
        self.env.company.product_label_show_price = False
        html_2x7 = self._render_simple_label("product.report_simple_label2x7")
        html_4x7 = self._render_simple_label("product.report_simple_label4x7")
        html_4x12 = self._render_simple_label("product.report_simple_label4x12")
        html_dymo = self._render_simple_label("product.report_simple_label_dymo")
        self.assertNotIn("o_label_price", html_2x7)
        self.assertNotIn("o_label_price_medium", html_4x7)
        self.assertNotIn("o_label_price_medium", html_4x12)
        self.assertNotIn("o_label_price_small", html_dymo)
        self.assertIn(self.product.barcode, html_2x7)
        self.assertIn(self.product.barcode, html_4x12)
