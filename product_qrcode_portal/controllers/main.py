from odoo import http
from odoo.http import request
from odoo.tools.translate import _


class ProductQRCodePortal(http.Controller):

    @http.route(
        ["/product-qr", "/product-qr/<string:code>"],
        type="http",
        auth="public",
        website=True,
        sitemap=False,
    )
    def product_qr_portal(self, code=None, company_id=None, **kwargs):
        website = request.website
        company = website._resolve_portal_qr_company(company_id)
        if company != website.company_id:
            alt_website = request.env["website"].sudo().search(
                [("company_id", "=", company.id)],
                limit=1,
            )
            if alt_website:
                website = alt_website
        product = website._find_product_by_qr_code(code, company=company)
        if not product or not website._is_product_qr_portal_allowed(product):
            return request.render(
                "product_qrcode_portal.product_qr_not_found",
                {
                    "code": website._extract_product_qr_code(code),
                    "error": _("No product matches this code."),
                },
            )
        target = website._get_product_qr_portal_target_url(product, company=company)
        if target:
            return request.redirect(target)
        return request.render(
            "product_qrcode_portal.product_qr_code",
            {
                "product": product,
                "code": product.qr_code,
            },
        )
