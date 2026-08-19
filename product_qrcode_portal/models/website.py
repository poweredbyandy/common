from urllib.parse import parse_qs, quote, unquote, urlparse

from odoo import fields, models


class Website(models.Model):
    _inherit = "website"

    product_qr_portal_action = fields.Selection(
        selection=[
            ("code", "Read product code only"),
            ("website_product", "Open website product page"),
            ("auto_order", "Open scan and order"),
        ],
        string="Product QR URL scan",
        default="code",
        required=True,
        help="What happens when a visitor scans the portal URL of a product.",
    )

    def _extract_product_qr_code(self, value):
        value = (value or "").strip().strip("\ufeff")
        if not value:
            return ""
        parsed = urlparse(value)
        params = parse_qs(parsed.query)
        codes = params.get("code") or []
        if codes and codes[0]:
            return unquote(codes[0]).strip()
        path = (parsed.path or "").rstrip("/")
        marker = "/product-qr"
        lower = path.lower()
        if lower.endswith(marker) or marker + "/" in lower + "/":
            suffix = path[lower.rfind(marker) + len(marker):].lstrip("/")
            if suffix:
                return unquote(suffix).strip()
        return value

    def _find_product_by_qr_code(self, value):
        self.ensure_one()
        code = self._extract_product_qr_code(value)
        if not code:
            return self.env["product.product"]
        Product = self.env["product.product"].sudo()
        product = Product.search(
            [
                "|",
                "|",
                ("barcode", "=", code),
                ("default_code", "=", code),
                ("qr_code", "=", code),
            ],
            limit=1,
        )
        if not product and code.isdigit():
            product = Product.browse(int(code)).exists()
        if product and product.active:
            return product
        return self.env["product.product"]

    def _is_product_qr_portal_allowed(self, product):
        self.ensure_one()
        return bool(
            product
            and product.active
            and product.sale_ok
            and product.website_published
        )

    def _get_product_qr_portal_url(self, product):
        self.ensure_one()
        code = product.qr_code
        if not code:
            return False
        return "%s/product-qr?code=%s" % (
            self.get_base_url().rstrip("/"),
            quote(str(code), safe=""),
        )

    def _get_product_qr_portal_target_url(self, product):
        self.ensure_one()
        product.ensure_one()
        code = product.qr_code
        action = self.product_qr_portal_action
        if action == "website_product" and product.website_url:
            return product.website_url
        if action == "auto_order" and code:
            return "/auto-order?code=%s" % quote(str(code), safe="")
        return False
