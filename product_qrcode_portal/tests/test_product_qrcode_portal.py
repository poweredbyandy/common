from odoo.tests import tagged
from odoo.addons.website.tools import MockRequest
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon
from odoo.addons.product_qrcode_portal.controllers.main import ProductQRCodePortal


@tagged("post_install", "-at_install")
class TestProductQRCodePortal(WebsiteSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.controller = ProductQRCodePortal()
        cls.product = cls.env["product.product"].create(
            {
                "name": "Portal Juice",
                "list_price": 10.0,
                "sale_ok": True,
                "website_published": True,
                "default_code": "PORTAL-01",
                "barcode": "8412345678999",
            }
        )

    def test_extract_raw_code(self):
        self.assertEqual(
            self.website._extract_product_qr_code("8412345678999"),
            "8412345678999",
        )

    def test_extract_code_from_portal_url(self):
        url = self.product.portal_qr_url
        self.assertIn("/product-qr?code=", url)
        self.assertEqual(
            self.website._extract_product_qr_code(url),
            self.product.qr_code,
        )

    def test_extract_code_from_auto_order_url(self):
        self.assertEqual(
            self.website._extract_product_qr_code(
                "https://shop.example/auto-order?code=PORTAL-01"
            ),
            "PORTAL-01",
        )

    def test_find_product_by_qr_code(self):
        product = self.website._find_product_by_qr_code(self.product.portal_qr_url)
        self.assertEqual(product, self.product)

    def test_portal_action_code_has_no_redirect(self):
        self.website.product_qr_portal_action = "code"
        self.assertFalse(self.website._get_product_qr_portal_target_url(self.product))

    def test_portal_action_website_product(self):
        self.website.product_qr_portal_action = "website_product"
        target = self.website._get_product_qr_portal_target_url(self.product)
        self.assertTrue(target)
        self.assertIn("/shop/", target)

    def test_portal_action_auto_order(self):
        self.website.product_qr_portal_action = "auto_order"
        target = self.website._get_product_qr_portal_target_url(self.product)
        self.assertIn("/auto-order?code=", target)
        self.assertIn(self.product.qr_code, target)

    def test_portal_qr_url(self):
        self.assertTrue(self.product.portal_qr_url)
        template = self.product.product_tmpl_id
        self.assertEqual(template.portal_qr_url, self.product.portal_qr_url)

    def test_controller_redirects_to_auto_order(self):
        self.website.product_qr_portal_action = "auto_order"
        website = self.website.with_user(self.public_user)
        with MockRequest(self.product.with_user(self.public_user).env, website=website):
            response = self.controller.product_qr_portal(code=self.product.qr_code)
        self.assertEqual(response.status_code, 303)
        self.assertIn("/auto-order?code=", response.location)
