import base64
import io

from PIL import Image

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPbaProductLabel(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Report = cls.env["report.pba_product_label.label_product_product_view"]
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test Label Product",
                "default_code": "SKU-001",
                "barcode": "7501234567890",
            }
        )

    def _png_logo(self):
        image = Image.new("RGB", (32, 32), (0, 0, 0))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue())

    def test_logo_gfa_from_company_image(self):
        gfa = self.Report._logo_to_zpl_gfa(self._png_logo())
        self.assertTrue(gfa.startswith("^FO100,30^GFA,"))
        self.assertTrue(gfa.endswith("^FS"))
        self.assertIn(",8,", gfa)
        self.assertIn("512,512,8,", gfa)

    def test_logo_gfa_empty_without_image(self):
        self.assertEqual(self.Report._logo_to_zpl_gfa(False), "")

    def test_company_logo_gfa_from_company(self):
        gfa = self.Report._company_logo_gfa(self.env.company)
        if self.env.company.logo or self.env.company.logo_web:
            self.assertTrue(gfa.startswith("^FO100,30^GFA,"))
            self.assertTrue(gfa.endswith("^FS"))

    def test_zpl_wizard_uses_pba_report(self):
        wizard = self.env["product.label.layout"].create(
            {
                "product_ids": [(6, 0, self.product.ids)],
                "print_format": "zpl",
                "custom_quantity": 1,
            }
        )
        xml_id, data = wizard._prepare_report_data()
        self.assertEqual(
            xml_id, "pba_product_label.action_report_label_product_product"
        )
        self.assertEqual(data["active_model"], "product.product")

    def test_render_includes_generated_logo_and_fields(self):
        self.env.company.logo = self._png_logo()
        wizard = self.env["product.label.layout"].create(
            {
                "product_ids": [(6, 0, self.product.ids)],
                "print_format": "zpl",
                "custom_quantity": 1,
            }
        )
        _xml_id, data = wizard._prepare_report_data()
        rendering, report_type = self.env["ir.actions.report"]._render_qweb_text(
            "pba_product_label.label_product_product_view",
            self.product.ids,
            data,
        )
        self.assertEqual(report_type, "text")
        text = rendering.decode("utf-8") if isinstance(rendering, bytes) else rendering
        self.assertIn("^XA", text)
        self.assertIn("^GFA,", text)
        self.assertIn("Test Label Product", text)
        self.assertIn("SKU-001", text)
        self.assertIn("7501234567890", text)
        self.assertIn("^XZ", text)
