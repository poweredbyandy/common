from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestProductQRCode(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env["product.product"].create(
            {
                "name": "QR Test Product",
                "default_code": "QR-REF-001",
                "barcode": "7501234567890",
            }
        )

    def test_qr_code_uses_barcode(self):
        self.assertEqual(self.product.qr_code, "7501234567890")

    def test_qr_code_falls_back_to_default_code(self):
        self.product.barcode = False
        self.assertEqual(self.product.qr_code, "QR-REF-001")

    def test_qr_code_falls_back_to_id(self):
        self.product.write({"barcode": False, "default_code": False})
        self.assertEqual(self.product.qr_code, str(self.product.id))

    def test_template_qr_fields(self):
        template = self.product.product_tmpl_id
        self.assertEqual(template.qr_code, self.product.qr_code)
