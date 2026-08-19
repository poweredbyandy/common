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
    def product_qr_portal(self, code=None, **kwargs):
        website = request.website
        product = website._find_product_by_qr_code(code)
        if not product or not website._is_product_qr_portal_allowed(product):
            return request.render(
                "product_qrcode_portal.product_qr_not_found",
                {
                    "code": website._extract_product_qr_code(code),
                    "error": _("No product matches this code."),
                },
            )
        target = website._get_product_qr_portal_target_url(product)
        if target:
            return request.redirect(target)
        return request.render(
            "product_qrcode_portal.product_qr_code",
            {
                "product": product,
                "code": product.qr_code,
            },
        )
