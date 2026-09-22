from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProductLabelPdf(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {
                "name": "PDF QR Label Product",
                "default_code": "PDF-QR-01",
                "barcode": "7501234567890",
                "list_price": 12.5,
            }
        )
        cls.pricelist = cls.env["product.pricelist"].search([], limit=1)
        if not cls.pricelist:
            cls.pricelist = cls.env["product.pricelist"].create({"name": "PDF Labels"})

    def _render_simple_label(self, xmlid):
        return self.env["ir.qweb"]._render(
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

    def test_pdf_labels_include_barcode_and_qr(self):
        templates = (
            "product.report_simple_label2x7",
            "product.report_simple_label4x7",
            "product.report_simple_label4x12",
            "product.report_simple_label4x12_no_price",
            "product.report_simple_label_dymo",
        )
        for xmlid in templates:
            html = str(self._render_simple_label(xmlid))
            self.assertIn("data:image/png;base64,", html)
            self.assertGreaterEqual(
                html.count("data:image/png;base64,"),
                2,
                "%s should print the barcode and the QR" % xmlid,
            )
            self.assertIn('class="o_label_qr"', html)
            self.assertIn(self.product.qr_code, html)
