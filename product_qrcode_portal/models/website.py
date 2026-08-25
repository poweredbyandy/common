from urllib.parse import parse_qs, quote, unquote, urlencode, urlparse

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
        required=False,
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

    def _extract_product_qr_company_id(self, value):
        value = (value or "").strip()
        if not value:
            return None
        parsed = urlparse(value)
        if not parsed.query:
            return None
        params = parse_qs(parsed.query)
        company_ids = params.get("company_id") or []
        if not company_ids or not str(company_ids[0]).isdigit():
            return None
        return int(company_ids[0])

    def _resolve_portal_qr_company(self, company_id=None):
        self.ensure_one()
        if company_id is not None:
            try:
                resolved_id = int(company_id)
            except (TypeError, ValueError):
                resolved_id = False
            if resolved_id:
                company = self.env["res.company"].sudo().browse(resolved_id).exists()
                if company:
                    return company
        return self.company_id

    def _portal_qr_product_company_domain(self, company):
        return [
            "|",
            ("company_id", "=", False),
            ("company_id", "in", company.ids),
        ]

    def _find_product_by_qr_code(self, value, company=None):
        self.ensure_one()
        company = company or self.company_id
        code = self._extract_product_qr_code(value)
        if not code:
            return self.env["product.product"]
        Product = self.env["product.product"].sudo()
        domain = self._portal_qr_product_company_domain(company) + [
            "|",
            "|",
            ("barcode", "=", code),
            ("default_code", "=", code),
            ("qr_code", "=", code),
        ]
        product = Product.search(domain, limit=1)
        if not product and code.isdigit():
            candidate = Product.browse(int(code)).exists()
            if (
                candidate
                and candidate.active
                and candidate.company_id in (False, company)
            ):
                product = candidate
        if product and product.active:
            return product
        return self.env["product.product"]

    def _is_product_qr_portal_allowed(self, product):
        self.ensure_one()
        if not (
            product
            and product.active
            and product.sale_ok
            and product.website_published
        ):
            return False
        template = product.product_tmpl_id
        if hasattr(template, "can_access_from_current_website"):
            return template.can_access_from_current_website(self.id)
        if template.website_id and template.website_id != self:
            return False
        return True

    def _get_product_qr_portal_url(self, product, company=None):
        self.ensure_one()
        code = product.qr_code
        if not code:
            return False
        company = company or self.company_id
        params = {
            "code": str(code),
            "company_id": company.id,
        }
        return "%s/product-qr?%s" % (
            self.get_base_url().rstrip("/"),
            urlencode(params),
        )

    def _get_product_qr_portal_target_url(self, product, company=None):
        self.ensure_one()
        product.ensure_one()
        code = product.qr_code
        company = company or self.company_id
        action = self.product_qr_portal_action
        if action == "website_product" and product.website_url:
            return product.website_url
        if action == "auto_order" and code:
            params = urlencode(
                {
                    "code": str(code),
                    "company_id": company.id,
                }
            )
            return "/auto-order?%s" % params
        return False
