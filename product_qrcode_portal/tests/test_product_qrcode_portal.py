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

    def _get_other_company(self):
        company = self.env["res.company"].search(
            [("id", "!=", self.website.company_id.id)], limit=1
        )
        if not company:
            self.skipTest("Second company is required")
        return company

    def _get_other_website(self):
        website = self.env["website"].search([("id", "!=", self.website.id)], limit=1)
        if not website:
            self.skipTest("Second website is required")
        return website

    def test_extract_raw_code(self):
        self.assertEqual(
            self.website._extract_product_qr_code("8412345678999"),
            "8412345678999",
        )

    def test_extract_code_from_portal_url(self):
        url = self.product.portal_qr_url
        self.assertIn("/product-qr?", url)
        self.assertIn("code=", url)
        self.assertIn("company_id=%s" % self.website.company_id.id, url)
        self.assertEqual(
            self.website._extract_product_qr_code(url),
            self.product.qr_code,
        )

    def test_extract_company_id_from_portal_url(self):
        url = self.website._get_product_qr_portal_url(self.product)
        self.assertEqual(
            self.website._extract_product_qr_company_id(url),
            self.website.company_id.id,
        )

    def test_extract_code_from_auto_order_url(self):
        self.assertEqual(
            self.website._extract_product_qr_code(
                "https://shop.example/auto-order?code=PORTAL-01&company_id=7"
            ),
            "PORTAL-01",
        )
        self.assertEqual(
            self.website._extract_product_qr_company_id(
                "https://shop.example/auto-order?code=PORTAL-01&company_id=7"
            ),
            7,
        )

    def test_find_product_by_qr_code(self):
        product = self.website._find_product_by_qr_code(self.product.portal_qr_url)
        self.assertEqual(product, self.product)

    def test_find_product_respects_company_id(self):
        other_company = self._get_other_company()
        self.env["product.product"].create(
            {
                "name": "Other Portal Juice",
                "list_price": 12.0,
                "sale_ok": True,
                "website_published": True,
                "default_code": "DUPE-CODE",
                "barcode": "8412345678998",
                "company_id": other_company.id,
            }
        )
        self.product.default_code = "DUPE-CODE"
        product = self.website._find_product_by_qr_code(
            "DUPE-CODE",
            company=self.website.company_id,
        )
        self.assertEqual(product, self.product)

    def test_portal_action_code_has_no_redirect(self):
        self.website.product_qr_portal_action = "code"
        self.assertFalse(self.website._get_product_qr_portal_target_url(self.product))

    def test_portal_action_empty_has_no_redirect(self):
        self.website.product_qr_portal_action = False
        self.assertFalse(self.website._get_product_qr_portal_target_url(self.product))

    def test_portal_action_website_product(self):
        self.website.product_qr_portal_action = "website_product"
        target = self.website._get_product_qr_portal_target_url(self.product)
        self.assertTrue(target)
        self.assertIn("/shop/", target)

    def test_portal_action_auto_order(self):
        self.website.product_qr_portal_action = "auto_order"
        target = self.website._get_product_qr_portal_target_url(self.product)
        self.assertIn("/auto-order?", target)
        self.assertIn("code=", target)
        self.assertIn("company_id=", target)
        self.assertIn(self.product.qr_code, target)

    def test_portal_qr_url(self):
        self.assertTrue(self.product.portal_qr_url)
        template = self.product.product_tmpl_id
        self.assertEqual(template.portal_qr_url, self.product.portal_qr_url)

    def test_template_portal_qr_url_depends_on_searchable_variants(self):
        field = self.env["product.template"]._fields["portal_qr_url"]
        self.assertIn("product_variant_ids.portal_qr_url", field.depends)
        self.assertNotIn("product_variant_id.portal_qr_url", field.depends)

    def test_portal_qr_url_uses_selected_website(self):
        other_website = self._get_other_website()
        url = other_website._get_product_qr_portal_url(self.product)
        self.assertIn("company_id=%s" % other_website.company_id.id, url)
        if other_website.domain:
            domain = other_website.domain.rstrip("/")
            self.assertTrue(url.startswith(domain) or domain in url)

    def test_controller_redirects_to_auto_order(self):
        self.website.product_qr_portal_action = "auto_order"
        website = self.website.with_user(self.public_user)
        with MockRequest(self.product.with_user(self.public_user).env, website=website):
            response = self.controller.product_qr_portal(
                code=self.product.qr_code,
                company_id=self.website.company_id.id,
            )
        self.assertEqual(response.status_code, 303)
        self.assertIn("/auto-order?", response.location)
        self.assertIn("company_id=", response.location)

    def test_wizard_prepares_portal_zpl_report_data(self):
        wizard = self.env["product.label.layout"].create(
            {
                "print_format": "qr_label_url",
                "custom_quantity": 1,
                "product_ids": [(6, 0, self.product.ids)],
                "portal_qr_website_id": self.website.id,
            }
        )
        xml_id, data = wizard._prepare_report_data()
        self.assertEqual(xml_id, "product_qrcode.action_report_product_qr_zpl")
        self.assertEqual(data["zpl_qr_mode"], "portal")
        self.assertEqual(data["portal_qr_website_id"], self.website.id)
        zpl = self.env[
            "report.product_qrcode.report_product_qr_zpl_document"
        ]._build_label_zpl(
            self.product,
            "portal",
            report_data=data,
        )
        expected_url = self.website._get_product_qr_portal_url(self.product)
        self.assertIn(expected_url, zpl)
        self.assertEqual(zpl.count("^BQN,2,4"), 1)
        self.assertIn("^BQN,2,3", zpl)
        self.assertIn("VER PRECIO", zpl)
        self.assertIn("^A0N,22,22", zpl)
        self.assertIn("^FO450,160", zpl)
        self.assertIn(self.product.qr_code, zpl)

    def test_wizard_defaults_portal_website(self):
        wizard = self.env["product.label.layout"].create(
            {
                "print_format": "qr_label_url",
                "custom_quantity": 1,
                "product_ids": [(6, 0, self.product.ids)],
            }
        )
        self.assertTrue(wizard.portal_qr_website_id)
