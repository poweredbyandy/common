from odoo import SUPERUSER_ID, http
from odoo.http import request
from odoo.tools.translate import _


class WebsiteAutoOrder(http.Controller):

    def _auto_order_website(self):
        return request.website._apply_auto_order_lang()

    @http.route(
        ["/auto-order"],
        type="http",
        auth="public",
        website=True,
        sitemap=True,
    )
    def auto_order(self, code=None, **kwargs):
        website = self._auto_order_website()
        if not website.has_ecommerce_access():
            return request.redirect("/web/login?redirect=/auto-order")
        target_lang = website._get_auto_order_lang()
        if target_lang and request.lang.code != target_lang.code:
            return request.redirect(website._get_auto_order_page_url(code=code))
        return request.render(
            "web_sale_auto_order.auto_order_page",
            {
                "auto_order_props": website._get_auto_order_boot_props(scan_code=code),
            },
        )

    @http.route(
        "/auto-order/scan",
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def auto_order_scan(self, code, quantity=None):
        website = self._auto_order_website()
        if not website.has_ecommerce_access():
            return {"error": _("You cannot access this page.")}
        website._apply_auto_order_pricelist()
        product = website._find_auto_order_product(code)
        if not product:
            return {"error": _("No product matches this code.")}
        return {
            "product": website._prepare_auto_order_product_data(
                product, quantity=quantity
            )
        }

    @http.route(
        "/auto-order/cart",
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def auto_order_cart(self):
        website = self._auto_order_website()
        if not website.has_ecommerce_access():
            return {"error": _("You cannot access this page.")}
        website._apply_auto_order_pricelist()
        return {"cart": website._get_auto_order_cart_data()}

    @http.route(
        "/auto-order/cart/add",
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def auto_order_cart_add(self, product_id, add_qty=1, set_qty=None, line_id=None):
        website = self._auto_order_website()
        if not website.has_ecommerce_access():
            return {"error": _("You cannot access this page.")}
        website._apply_auto_order_pricelist()
        product = request.env["product.product"].sudo().browse(int(product_id))
        if not product.exists() or not website._is_auto_order_product_allowed(product):
            return {"error": _("This product cannot be added to the cart.")}
        order = website.sale_get_order(force_create=True)
        if order.state != "draft":
            request.session["sale_order_id"] = None
            order = website.sale_get_order(force_create=True)
        order = order.with_user(SUPERUSER_ID).with_context(
            **website._auto_order_cart_context()
        )
        if set_qty is not None:
            order._cart_update(
                product_id=product.id,
                line_id=line_id,
                add_qty=None,
                set_qty=set_qty,
            )
        else:
            order._cart_update(product_id=product.id, add_qty=add_qty)
        request.session["website_sale_cart_quantity"] = order.cart_quantity
        return {"cart": website._get_auto_order_cart_data()}

    @http.route(
        "/auto-order/cart/update",
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def auto_order_cart_update(self, line_id, set_qty=0):
        website = self._auto_order_website()
        if not website.has_ecommerce_access():
            return {"error": _("You cannot access this page.")}
        website._apply_auto_order_pricelist()
        return website._auto_order_update_line_qty(line_id, set_qty)

    @http.route(
        "/auto-order/cart/line/remove",
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def auto_order_cart_line_remove(self, line_id):
        website = self._auto_order_website()
        if not website.has_ecommerce_access():
            return {"error": _("You cannot access this page.")}
        website._apply_auto_order_pricelist()
        return website._auto_order_remove_line(line_id)

    @http.route(
        "/auto-order/cart/clear",
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def auto_order_cart_clear(self):
        website = self._auto_order_website()
        if not website.has_ecommerce_access():
            return {"error": _("You cannot access this page.")}
        return website._auto_order_clear_cart()

    @http.route(
        "/auto-order/cart/buy",
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def auto_order_cart_buy(self):
        website = self._auto_order_website()
        if not website.has_ecommerce_access():
            return {"error": _("You cannot access this page.")}
        website._apply_auto_order_pricelist()
        return website._auto_order_buy()

    @http.route(
        "/auto-order/order/lookup-vat",
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def auto_order_order_lookup_vat(self, vat):
        website = self._auto_order_website()
        if not website.has_ecommerce_access():
            return {"error": _("You cannot access this page.")}
        return website._auto_order_lookup_vat(vat)

    @http.route(
        "/auto-order/order/register",
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def auto_order_order_register(self, vat, name="", phone="", email=""):
        website = self._auto_order_website()
        if not website.has_ecommerce_access():
            return {"error": _("You cannot access this page.")}
        return website._auto_order_register_customer(vat, name, phone, email)

    @http.route(
        "/auto-order/order/finish",
        type="json",
        auth="public",
        website=True,
        methods=["POST"],
    )
    def auto_order_order_finish(self):
        website = self._auto_order_website()
        if not website.has_ecommerce_access():
            return {"error": _("You cannot access this page.")}
        return website._auto_order_finish()
