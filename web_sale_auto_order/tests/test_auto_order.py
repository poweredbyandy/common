from odoo.tests import tagged
from odoo.addons.website.tools import MockRequest
from odoo.addons.website_sale.tests.common import WebsiteSaleCommon
from odoo.addons.web_sale_auto_order.controllers.main import WebsiteAutoOrder


@tagged("post_install", "-at_install")
class TestWebSaleAutoOrder(WebsiteSaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.controller = WebsiteAutoOrder()
        cls.scan_product = cls.env["product.product"].create(
            {
                "name": "Scanner Juice",
                "list_price": 10.0,
                "sale_ok": True,
                "website_published": True,
                "default_code": "JUICE-01",
                "barcode": "8412345678901",
                "description": "<p>Keep refrigerated</p>",
            }
        )
        cls.other_currency = cls.env.ref("base.EUR")
        if cls.env.company.currency_id == cls.other_currency:
            cls.other_currency = cls.env.ref("base.USD")
        cls.env["res.currency.rate"].create(
            {
                "name": "2020-01-01",
                "currency_id": cls.other_currency.id,
                "rate": 2.0,
                "company_id": cls.env.company.id,
            }
        )
        cls.auto_pricelist = cls.env["product.pricelist"].create(
            {
                "name": "Auto Order Pricelist",
                "currency_id": cls.other_currency.id,
                "website_id": cls.website.id,
            }
        )

    def _request_env(self):
        return self.scan_product.with_user(self.public_user).env

    def test_scan_finds_unpublished_sale_ok_product(self):
        self.scan_product.website_published = False
        with MockRequest(self._request_env(), website=self.website.with_user(self.public_user)):
            result = self.controller.auto_order_scan(code="8412345678901")
        self.assertNotIn("error", result)
        self.assertEqual(result["product"]["id"], self.scan_product.id)

    def test_scan_finds_product_by_barcode(self):
        with MockRequest(self._request_env(), website=self.website.with_user(self.public_user)):
            result = self.controller.auto_order_scan(code="8412345678901")
        self.assertNotIn("error", result)
        self.assertEqual(result["product"]["id"], self.scan_product.id)
        self.assertIn("Keep refrigerated", result["product"]["internal_notes"])
        self.assertTrue(result["product"]["price_pricelist_taxed_formatted"])
        self.assertTrue(result["product"]["price_company_taxed_formatted"])

    def test_scan_finds_product_from_portal_url(self):
        if "portal_qr_url" not in self.scan_product._fields:
            self.skipTest("product_qrcode_portal is not installed")
        website = self.website.with_user(self.public_user)
        with MockRequest(self._request_env(), website=website):
            result = self.controller.auto_order_scan(
                code=self.scan_product.portal_qr_url
            )
        self.assertEqual(result["product"]["id"], self.scan_product.id)

    def test_scan_finds_product_from_auto_order_url(self):
        website = self.website.with_user(self.public_user)
        with MockRequest(self._request_env(), website=website):
            result = self.controller.auto_order_scan(
                code="/auto-order?code=%s" % self.scan_product.qr_code
            )
        self.assertEqual(result["product"]["id"], self.scan_product.id)

    def test_boot_props_skip_cart_and_product(self):
        website = self.website.with_user(self.public_user)
        with MockRequest(self._request_env(), website=website):
            props = website._get_auto_order_boot_props(
                scan_code=self.scan_product.barcode
            )
        self.assertEqual(props["scanCode"], self.scan_product.barcode)
        self.assertEqual(props["buttonColor"], "#10b981")
        self.assertEqual(props["buttonTextColor"], "#052e16")
        self.assertNotIn("cart", props)
        self.assertNotIn("product", props)

    def test_frontend_loads_auto_order_translations(self):
        modules = self.env["ir.http"]._get_translation_frontend_modules_name()
        self.assertIn("web_sale_auto_order", modules)

    def test_kiosk_language_falls_back_to_website_default(self):
        website = self.website
        self.assertEqual(website._get_auto_order_lang(), website.default_lang_id)
        spanish = self.env["res.lang"].search([("code", "like", "es_%")], limit=1)
        if not spanish:
            self.skipTest("No Spanish language is installed")
        if spanish not in website.language_ids:
            website.language_ids = [(4, spanish.id)]
        website.auto_order_lang_id = spanish
        self.assertEqual(website._get_auto_order_lang(), spanish)

    def test_configured_button_colors(self):
        self.website.auto_order_button_color = "#FF5500"
        self.website.auto_order_button_text_color = "#FFFFFF"
        website = self.website.with_user(self.public_user)
        with MockRequest(self._request_env(), website=website):
            props = website._get_auto_order_boot_props()
        self.assertEqual(props["buttonColor"], "#ff5500")
        self.assertEqual(props["buttonTextColor"], "#ffffff")
        self.website.auto_order_button_color = "red;background:url(x)"
        with MockRequest(self._request_env(), website=website):
            props = website._get_auto_order_boot_props()
        self.assertEqual(props["buttonColor"], "#10b981")

    def test_page_props_open_product_from_code(self):
        website = self.website.with_user(self.public_user)
        with MockRequest(self._request_env(), website=website):
            props = website._get_auto_order_page_props(
                scan_code=self.scan_product.barcode
            )
        self.assertEqual(props["product"]["id"], self.scan_product.id)

    def test_scan_finds_product_by_qr_code(self):
        with MockRequest(self._request_env(), website=self.website.with_user(self.public_user)):
            result = self.controller.auto_order_scan(code=self.scan_product.qr_code)
        self.assertEqual(result["product"]["id"], self.scan_product.id)

    def test_scan_unknown_code(self):
        with MockRequest(self._request_env(), website=self.website.with_user(self.public_user)):
            result = self.controller.auto_order_scan(code="UNKNOWN-CODE")
        self.assertTrue(result.get("error"))

    def test_decrement_last_unit_removes_line(self):
        website = self.website.with_user(self.public_user)
        with MockRequest(self._request_env(), website=website):
            added = self.controller.auto_order_cart_add(
                product_id=self.scan_product.id, add_qty=1
            )
            self.assertEqual(added["cart"]["line_count"], 1)
            line_id = added["cart"]["lines"][0]["id"]
            updated = self.controller.auto_order_cart_update(
                line_id=line_id, set_qty=0
            )
            self.assertEqual(updated["cart"]["line_count"], 0)
            self.assertFalse(updated["cart"]["lines"])

    def test_scan_shows_quantity_already_in_cart(self):
        website = self.website.with_user(self.public_user)
        with MockRequest(self._request_env(), website=website):
            added = self.controller.auto_order_cart_add(
                product_id=self.scan_product.id, add_qty=6
            )
            self.assertEqual(added["cart"]["lines"][0]["quantity"], 6)
            scanned = self.controller.auto_order_scan(code="8412345678901")
        self.assertEqual(scanned["product"]["quantity"], 6)
        self.assertEqual(
            scanned["product"]["line_id"], added["cart"]["lines"][0]["id"]
        )

    def test_remove_last_line_resets_cart(self):
        website = self.website.with_user(self.public_user)
        with MockRequest(self._request_env(), website=website):
            added = self.controller.auto_order_cart_add(
                product_id=self.scan_product.id, add_qty=1
            )
            line_id = added["cart"]["lines"][0]["id"]
            removed = self.controller.auto_order_cart_line_remove(line_id=line_id)
        self.assertFalse(removed.get("error"))
        self.assertEqual(removed["cart"]["line_count"], 0)
        self.assertFalse(removed["cart"]["lines"])
        self.assertFalse(removed["cart"]["order_id"])

    def test_add_and_clear_cart(self):
        website = self.website.with_user(self.public_user)
        with MockRequest(self._request_env(), website=website):
            added = self.controller.auto_order_cart_add(
                product_id=self.scan_product.id, add_qty=2
            )
            self.assertEqual(added["cart"]["line_count"], 2)
            self.assertEqual(len(added["cart"]["lines"]), 1)
            cleared = self.controller.auto_order_cart_clear()
            self.assertEqual(cleared["cart"]["line_count"], 0)

    def test_buy_saves_order_number(self):
        self.website.auto_order_success_message = "Continue at the cashier to pay."
        website = self.website.with_user(self.public_user)
        with MockRequest(self._request_env(), website=website):
            empty = self.controller.auto_order_cart_buy()
            self.assertTrue(empty.get("error"))
            self.controller.auto_order_cart_add(
                product_id=self.scan_product.id, add_qty=1
            )
            bought = self.controller.auto_order_cart_buy()
            self.assertFalse(bought.get("error"))
            self.assertTrue(bought["orderName"])
            self.assertEqual(bought["cart"]["line_count"], 0)
            self.assertIn("cashier", bought["extraMessage"])
            missing = self.controller.auto_order_order_register(vat="")
            self.assertTrue(missing.get("error"))
            unknown = self.controller.auto_order_order_lookup_vat(vat="V28493778")
            self.assertFalse(unknown.get("error"))
            self.assertFalse(unknown.get("exists"))
            self.assertFalse(unknown.get("name"))
            self.assertEqual(set(unknown.keys()), {"exists", "name"})
            registered = self.controller.auto_order_order_register(
                vat="V28493778",
                name="Ana Perez",
                phone="04141234567",
                email="ana@example.com",
            )
            if registered.get("error"):
                return
            self.assertTrue(registered.get("ok"))
            order = self.env["sale.order"].search(
                [("name", "=", bought["orderName"])], limit=1
            )
            self.assertEqual(order.partner_id.name, "Ana Perez")
            existing_name = order.partner_id.name
            lookup = self.controller.auto_order_order_lookup_vat(vat="V28493778")
            self.assertTrue(lookup.get("exists"))
            self.assertEqual(lookup.get("name"), existing_name)
            self.assertNotIn("phone", lookup)
            self.assertNotIn("email", lookup)
            linked = self.controller.auto_order_order_register(vat="V28493778")
            self.assertTrue(linked.get("ok"))
            self.assertEqual(order.partner_id.name, existing_name)
            finished = self.controller.auto_order_order_finish()
            self.assertTrue(finished.get("ok"))

    def test_configured_pricelist_currency(self):
        self.website.auto_order_pricelist_id = self.auto_pricelist
        website = self.website.with_user(self.public_user)
        with MockRequest(self._request_env(), website=website):
            result = self.controller.auto_order_scan(code="JUICE-01")
        product = result["product"]
        same_currency = self.env.company.currency_id == self.other_currency
        self.assertEqual(product["same_currency"], same_currency)
        self.assertEqual(product["pricelist_currency_name"], self.other_currency.name)
        self.assertEqual(
            product["company_currency_name"], self.env.company.currency_id.name
        )
        with MockRequest(self._request_env(), website=website):
            added = self.controller.auto_order_cart_add(
                product_id=self.scan_product.id, add_qty=1
            )
        if same_currency:
            self.assertFalse(added["cart"].get("rateLabel"))
        else:
            self.assertIn("1", added["cart"]["rateLabel"])
            self.assertIn("=", added["cart"]["rateLabel"])
