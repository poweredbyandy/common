import base64
import io

from PIL import Image

from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProductQrZpl(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report = cls.env["report.product_qrcode.report_product_qr_zpl_document"]
        cls.product = cls.env["product.product"].create(
            {
                "name": "Alternador Bosch 14V para Ford Cargo 815 y 1721",
                "default_code": "3C45-10300-AA",
                "barcode": "7501234567890",
            }
        )

    def test_build_label_zpl_contains_product_data(self):
        zpl = self.report._build_label_zpl(self.product, "product")
        self.assertIn("^XA", zpl)
        self.assertIn("^XZ", zpl)
        self.assertIn("7501234567890", zpl)
        self.assertIn("3C45-10300-AA", zpl)
        self.assertIn("Alternador Bosch", zpl)
        self.assertNotIn("Cargo 815 / 1721", zpl)

    def test_product_mode_keeps_single_qr_and_original_code_position(self):
        zpl = self.report._build_label_zpl(self.product, "product")
        self.assertEqual(zpl.count("^BQN"), 1)
        self.assertNotIn("^BQN,2,3", zpl)
        self.assertIn("^FO280,125", zpl)
        self.assertIn("^FO280,145", zpl)

        self.assertEqual(
            self.report._zpl_sanitize("A^B~C\\D"),
            "A B C D",
        )

    def test_zpl_wrap_name_splits_long_text(self):
        wrapped = self.report._zpl_wrap_name(
            "Alternador Bosch 14V para Ford Cargo 815 y 1721",
            max_chars=26,
            max_lines=3,
        )
        self.assertIn(r"\&", wrapped)

    def test_wizard_prepares_zpl_report_data(self):
        wizard = self.env["product.label.layout"].create(
            {
                "print_format": "qr_label_code",
                "custom_quantity": 2,
                "product_ids": [(6, 0, self.product.ids)],
            }
        )
        xml_id, data = wizard._prepare_report_data()
        self.assertEqual(xml_id, "product_qrcode.action_report_product_qr_zpl")
        self.assertEqual(data["zpl_qr_mode"], "product")
        self.assertEqual(data["quantity_by_product"][str(self.product.id)], 2)

    def test_report_builds_multiple_copies(self):
        data = {
            "active_model": "product.product",
            "quantity_by_product": {str(self.product.id): 2},
            "zpl_qr_mode": "product",
        }
        zpl_body = self.report._build_zpl_body(data)
        self.assertEqual(zpl_body.count("^XZ"), 2)

    def test_missing_qr_code_raises_user_error(self):
        product = self.env["product.product"].new({"name": "Draft Product"})
        with self.assertRaises(UserError):
            self.report._build_label_zpl(product, "product")

    def _png_b64(self, color=(0, 0, 0)):
        image = Image.new("RGB", (16, 16), color)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue())

    def test_label_uses_qr_label_logo(self):
        self.env.company.qr_label_logo = self._png_b64()
        zpl = self.report._build_label_zpl(self.product, "product")
        self.assertIn("^GFA,", zpl)

    def test_label_falls_back_to_company_logo(self):
        self.env.company.write(
            {
                "qr_label_logo": False,
                "logo": self._png_b64((20, 20, 20)),
            }
        )
        self.assertFalse(self.env.company.uses_default_logo)
        zpl = self.report._build_label_zpl(self.product, "product")
        self.assertIn("^GFA,", zpl)

    def test_label_skips_default_company_logo(self):
        self.env.company.write(
            {
                "qr_label_logo": False,
                "logo": self.env["res.company"]._get_logo(),
            }
        )
        self.assertTrue(self.env.company.uses_default_logo)
        zpl = self.report._build_label_zpl(self.product, "product")
        self.assertNotIn("^GFA,", zpl)
