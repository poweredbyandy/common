import logging
import re
from urllib.parse import parse_qs, unquote, urlencode, urlparse

from odoo import SUPERUSER_ID, _, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.http import request
from odoo.tools import html2plaintext
from odoo.tools.misc import formatLang, format_amount

_logger = logging.getLogger(__name__)

AUTO_ORDER_BUTTON_COLOR_DEFAULT = "#10b981"
AUTO_ORDER_BUTTON_TEXT_COLOR_DEFAULT = "#052e16"
_AUTO_ORDER_HEX_COLOR = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


class Website(models.Model):
    _inherit = "website"

    auto_order_pricelist_id = fields.Many2one(
        comodel_name="product.pricelist",
        string="Auto Order Pricelist",
        help="Pricelist used on the scan and order portal. "
        "If empty, the current website pricelist is used.",
    )
    auto_order_button_color = fields.Char(
        string="Button Color",
        default=AUTO_ORDER_BUTTON_COLOR_DEFAULT,
        help="Background color of the main buttons on /auto-order.",
    )
    auto_order_button_text_color = fields.Char(
        string="Button Text Color",
        default=AUTO_ORDER_BUTTON_TEXT_COLOR_DEFAULT,
        help="Text color of the main buttons on /auto-order.",
    )
    auto_order_success_message = fields.Text(
        string="Success Extra Message",
        translate=True,
        default="Continue at the cashier to pay.",
        help="Extra text shown after Buy on /auto-order, under the saved order number.",
    )
    auto_order_lang_id = fields.Many2one(
        comodel_name="res.lang",
        string="Kiosk Language",
        help="Language used on /auto-order. The language must be active on the "
        "website. Leave empty to use the website default language.",
    )

    def _sanitize_auto_order_color(self, value, default):
        color = (value or "").strip()
        if not _AUTO_ORDER_HEX_COLOR.match(color):
            return default
        if len(color) == 4:
            color = "#" + "".join(char * 2 for char in color[1:])
        return color.lower()

    def _get_auto_order_button_colors(self):
        self.ensure_one()
        return {
            "buttonColor": self._sanitize_auto_order_color(
                self.auto_order_button_color,
                AUTO_ORDER_BUTTON_COLOR_DEFAULT,
            ),
            "buttonTextColor": self._sanitize_auto_order_color(
                self.auto_order_button_text_color,
                AUTO_ORDER_BUTTON_TEXT_COLOR_DEFAULT,
            ),
        }

    def _get_auto_order_button_color(self):
        return self._get_auto_order_button_colors()["buttonColor"]

    def _get_auto_order_lang(self):
        self.ensure_one()
        return self.auto_order_lang_id or self.default_lang_id

    def _apply_auto_order_lang(self):
        self.ensure_one()
        lang = self._get_auto_order_lang()
        if not lang:
            return self
        request.update_context(lang=lang.code)
        session_context = dict(request.session.get("context") or {})
        session_context["lang"] = lang.code
        request.session["context"] = session_context
        return self.with_context(lang=lang.code)

    def _get_auto_order_page_url(self, code=None):
        self.ensure_one()
        path = "/auto-order"
        if code:
            path = "%s?%s" % (path, urlencode({"code": code}))
        lang = self._get_auto_order_lang()
        return request.env["ir.http"]._url_for(
            path, lang_code=lang.code if lang else None
        )

    def _get_auto_order_pricelist(self):
        self.ensure_one()
        return self.auto_order_pricelist_id or self.sudo().pricelist_id

    def _get_auto_order_rate_label(self, currency_a, currency_b):
        self.ensure_one()
        if not currency_a or not currency_b or currency_a == currency_b:
            return ""
        company = self.company_id
        date = fields.Date.context_today(self)
        rate = currency_a._get_conversion_rate(currency_a, currency_b, company, date)
        if not rate:
            return ""
        if rate >= 1:
            strong, weak, value = currency_a, currency_b, rate
        else:
            strong, weak, value = currency_b, currency_a, 1.0 / rate
        if abs(value - round(value)) < 0.005:
            amount = "%s" % int(round(value))
        else:
            amount = formatLang(self.env, value, digits=2)
        return "1%s = %s %s" % (
            (strong.symbol or strong.name).strip(),
            amount,
            (weak.symbol or weak.name).strip(),
        )

    def _apply_auto_order_pricelist(self):
        self.ensure_one()
        pricelist = self.auto_order_pricelist_id
        if not pricelist:
            return self.pricelist_id
        request.session["website_sale_current_pl"] = pricelist.id
        request.session["website_sale_selected_pl_id"] = pricelist.id
        order = self.sale_get_order()
        if order:
            order._cart_update_pricelist(pricelist_id=pricelist.id)
        return pricelist

    def _extract_auto_order_code(self, code):
        if hasattr(self, "_extract_product_qr_code"):
            return self._extract_product_qr_code(code)
        value = (code or "").strip().strip("\ufeff")
        if not value:
            return ""
        parsed = urlparse(value)
        params = parse_qs(parsed.query)
        codes = params.get("code") or []
        if codes and codes[0]:
            return unquote(codes[0]).strip()
        return value

    def _find_auto_order_product(self, code):
        self.ensure_one()
        if hasattr(self, "_find_product_by_qr_code"):
            product = self._find_product_by_qr_code(code)
        else:
            product = self._find_product_by_auto_order_code(code)
        if product and self._is_auto_order_product_allowed(product):
            return product
        return self.env["product.product"]

    def _find_product_by_auto_order_code(self, value):
        self.ensure_one()
        extracted = self._extract_auto_order_code(value)
        if not extracted:
            return self.env["product.product"]
        Product = self.env["product.product"].sudo()
        product = Product.search(
            [
                "|",
                "|",
                ("barcode", "=", extracted),
                ("default_code", "=", extracted),
                ("qr_code", "=", extracted),
            ],
            limit=1,
        )
        if not product and extracted.isdigit():
            product = Product.browse(int(extracted)).exists()
        if product and product.active:
            return product
        return self.env["product.product"]

    def _is_auto_order_product_allowed(self, product):
        self.ensure_one()
        return bool(
            product
            and product.active
            and product.sale_ok
            and self.has_ecommerce_access()
        )

    def _get_auto_order_boot_props(self, scan_code=None):
        self.ensure_one()
        company_currency = self.company_id.currency_id
        pricelist = self.auto_order_pricelist_id
        pricelist_currency = pricelist.currency_id if pricelist else company_currency
        props = {
            "companyCurrencyName": company_currency.name,
            "pricelistCurrencyName": pricelist_currency.name,
            "sameCurrency": company_currency == pricelist_currency,
            "scanCode": scan_code or "",
        }
        props.update(self._get_auto_order_button_colors())
        return props

    def _get_auto_order_page_props(self, scan_code=None):
        self.ensure_one()
        pricelist = self._apply_auto_order_pricelist()
        company_currency = self.company_id.currency_id
        props = {
            "cart": self._get_auto_order_cart_data(),
            "companyCurrencyName": company_currency.name,
            "pricelistCurrencyName": pricelist.currency_id.name,
            "sameCurrency": company_currency == pricelist.currency_id,
        }
        props.update(self._get_auto_order_button_colors())
        if scan_code:
            product = self._find_auto_order_product(scan_code)
            if product:
                props["product"] = self._prepare_auto_order_product_data(product)
            else:
                props["scanError"] = _("No product matches this code.")
        return props

    def _get_auto_order_cart_line_for_product(self, product):
        self.ensure_one()
        order = self._get_auto_order_session_order()
        if not order:
            return self.env["sale.order.line"]
        return order.order_line.filtered(
            lambda rec: rec.product_id.id == product.id and rec._show_in_cart()
        )

    def _prepare_auto_order_product_data(self, product, quantity=None):
        self.ensure_one()
        product.ensure_one()
        lines = self._get_auto_order_cart_line_for_product(product)
        if quantity is None:
            quantity = sum(lines.mapped("product_uom_qty")) or 1.0
        prices = self._get_auto_order_prices(product, quantity)
        notes = html2plaintext(product.description or "") if product.description else ""
        notes = (notes or "").replace("\r\n", "\n").replace("\r", "\n").strip()
        return {
            "id": product.id,
            "name": product.display_name,
            "barcode": product.barcode or "",
            "default_code": product.default_code or "",
            "qr_code": product.qr_code or "",
            "image_url": "/web/image/product.product/%s/image_128" % product.id,
            "uom_name": product.uom_id.name,
            "internal_notes": notes,
            "quantity": quantity,
            "line_id": lines[:1].id,
            **prices,
        }

    def _get_auto_order_prices(self, product, quantity=1.0):
        self.ensure_one()
        company = self.company_id
        company_currency = company.currency_id
        pricelist = self._get_auto_order_pricelist()
        partner = request.env.user.partner_id
        date = fields.Date.context_today(self)
        unit_price = pricelist._get_product_price(product, quantity or 1.0)
        product_taxes = product.sudo().taxes_id._filter_taxes_by_company(company)
        taxes = self.env["account.tax"]
        if product_taxes:
            taxes = self.fiscal_position_id.sudo().map_tax(product_taxes)
            unit_price = product._get_tax_included_unit_price_from_price(
                unit_price,
                product_taxes,
                product_taxes_after_fp=taxes,
            )
        qty = quantity or 1.0
        pl_taxes = taxes.compute_all(
            unit_price,
            pricelist.currency_id,
            qty,
            product=product,
            partner=partner,
        )
        company_unit_price = pricelist.currency_id._convert(
            unit_price,
            company_currency,
            company,
            date,
        )
        company_taxes = taxes.compute_all(
            company_unit_price,
            company_currency,
            qty,
            product=product,
            partner=partner,
        )
        tax_details = [
            {
                "name": tax.get("name"),
                "amount_pricelist": tax.get("amount"),
                "amount_company": company_currency.round(
                    pricelist.currency_id._convert(
                        tax.get("amount") or 0.0,
                        company_currency,
                        company,
                        date,
                    )
                ),
                "amount_pricelist_formatted": format_amount(
                    self.env, tax.get("amount") or 0.0, pricelist.currency_id
                ),
                "amount_company_formatted": format_amount(
                    self.env,
                    company_currency.round(
                        pricelist.currency_id._convert(
                            tax.get("amount") or 0.0,
                            company_currency,
                            company,
                            date,
                        )
                    ),
                    company_currency,
                ),
            }
            for tax in pl_taxes.get("taxes", [])
        ]
        return {
            "same_currency": company_currency == pricelist.currency_id,
            "company_currency_name": company_currency.name,
            "pricelist_currency_name": pricelist.currency_id.name,
            "price_company_untaxed": company_taxes["total_excluded"],
            "price_company_taxed": company_taxes["total_included"],
            "price_pricelist_untaxed": pl_taxes["total_excluded"],
            "price_pricelist_taxed": pl_taxes["total_included"],
            "price_company_untaxed_formatted": format_amount(
                self.env, company_taxes["total_excluded"], company_currency
            ),
            "price_company_taxed_formatted": format_amount(
                self.env, company_taxes["total_included"], company_currency
            ),
            "price_pricelist_untaxed_formatted": format_amount(
                self.env, pl_taxes["total_excluded"], pricelist.currency_id
            ),
            "price_pricelist_taxed_formatted": format_amount(
                self.env, pl_taxes["total_included"], pricelist.currency_id
            ),
            "tax_details": tax_details,
        }

    def _get_auto_order_session_order(self):
        sale_order_id = request.session.get("sale_order_id") if request else None
        if not sale_order_id:
            return self.env["sale.order"]
        return (
            self.env["sale.order"]
            .with_user(SUPERUSER_ID)
            .browse(sale_order_id)
            .exists()
        )

    def _auto_order_sudo_order(self):
        self.ensure_one()
        order = self.sale_get_order()
        if not order:
            return self.env["sale.order"]
        return order.with_user(SUPERUSER_ID)

    def _auto_order_cart_context(self):
        return {
            "tracking_disable": True,
            "mail_notrack": True,
            "mail_create_nolog": True,
        }

    def _auto_order_visible_lines(self, order):
        return order.order_line.filtered(lambda rec: rec._show_in_cart())

    def _auto_order_abandon_cart(self, order=None):
        self.ensure_one()
        order = (order or self._auto_order_sudo_order()).with_user(SUPERUSER_ID)
        self.sale_reset()
        if order:
            try:
                with self.env.cr.savepoint():
                    order.with_context(
                        **self._auto_order_cart_context()
                    ).order_line.unlink()
            except AccessError:
                _logger.debug(
                    "Could not unlink auto-order cart lines after reset.",
                    exc_info=True,
                )
        return self._get_auto_order_empty_cart()

    def _auto_order_remove_line(self, line_id):
        self.ensure_one()
        order = self._auto_order_sudo_order()
        if not order:
            return {"cart": self._get_auto_order_empty_cart()}
        line = order.order_line.filtered(lambda rec: rec.id == int(line_id))[:1]
        if not line:
            return {"error": _("Cart line not found.")}
        remaining = self._auto_order_visible_lines(order) - line
        if not remaining:
            return {"cart": self._auto_order_abandon_cart(order)}
        line.with_context(**self._auto_order_cart_context()).unlink()
        return {"cart": self._get_auto_order_cart_data()}

    def _auto_order_update_line_qty(self, line_id, set_qty):
        self.ensure_one()
        qty = float(set_qty or 0)
        if qty <= 0:
            return self._auto_order_remove_line(line_id)
        order = self._auto_order_sudo_order()
        if not order:
            return {"cart": self._get_auto_order_empty_cart()}
        line = order.order_line.filtered(lambda rec: rec.id == int(line_id))[:1]
        if not line:
            return {"error": _("Cart line not found.")}
        order.with_context(**self._auto_order_cart_context())._cart_update(
            product_id=line.product_id.id,
            line_id=line.id,
            add_qty=None,
            set_qty=qty,
        )
        request.session["website_sale_cart_quantity"] = int(
            sum(self._auto_order_visible_lines(order).mapped("product_uom_qty"))
        )
        return {"cart": self._get_auto_order_cart_data()}

    def _auto_order_clear_cart(self):
        self.ensure_one()
        return {"cart": self._auto_order_abandon_cart()}

    def _auto_order_saved_order(self):
        order_id = request.session.get("auto_order_checkout_id") if request else None
        if not order_id:
            return self.env["sale.order"]
        return (
            self.env["sale.order"].with_user(SUPERUSER_ID).browse(int(order_id)).exists()
        )

    def _get_auto_order_success_message(self):
        self.ensure_one()
        return (self.auto_order_success_message or "").strip()

    def _auto_order_buy(self):
        self.ensure_one()
        order = self._auto_order_sudo_order()
        if not order or not self._auto_order_visible_lines(order):
            return {"error": _("There are no products in the cart.")}
        request.session["auto_order_checkout_id"] = order.id
        self.sale_reset()
        request.session["auto_order_checkout_id"] = order.id
        return {
            "orderName": order.name,
            "extraMessage": self._get_auto_order_success_message(),
            "cart": self._get_auto_order_empty_cart(),
        }

    def _auto_order_normalize_vat(self, vat):
        return re.sub(r"[^A-Z0-9]", "", (vat or "").upper())

    def _auto_order_vat_search_values(self, vat):
        clean = self._auto_order_normalize_vat(vat)
        if not clean:
            return []
        values = {clean, (vat or "").strip()}
        if clean[0].isalpha():
            values.add(clean[1:])
            values.add("%s-%s" % (clean[0], clean[1:]))
        else:
            values.add("V%s" % clean)
        return [value for value in values if value]

    def _auto_order_vat_matches(self, left, right):
        first = self._auto_order_normalize_vat(left)
        second = self._auto_order_normalize_vat(right)
        if not first or not second:
            return False
        if first == second:
            return True
        if first[0].isalpha() and first[1:] == second:
            return True
        if second[0].isalpha() and second[1:] == first:
            return True
        return False

    def _auto_order_find_partner_by_vat(self, vat):
        values = self._auto_order_vat_search_values(vat)
        if not values:
            return self.env["res.partner"]
        partners = (
            self.env["res.partner"]
            .with_user(SUPERUSER_ID)
            .search(
                [
                    ("vat", "in", values),
                    ("company_id", "in", [False, self.company_id.id]),
                ],
                limit=20,
            )
        )
        for partner in partners:
            if self._auto_order_vat_matches(partner.vat, vat):
                return partner
        return self.env["res.partner"]

    def _auto_order_lookup_vat(self, vat):
        self.ensure_one()
        if not self._auto_order_saved_order():
            return {"error": _("The order is no longer available.")}
        if not self._auto_order_normalize_vat(vat):
            return {"error": _("Please fill in the RIF.")}
        partner = self._auto_order_find_partner_by_vat(vat)
        return {
            "exists": bool(partner),
            "name": partner.name if partner else "",
        }

    def _auto_order_assign_order_partner(self, order, partner):
        order.with_context(**self._auto_order_cart_context()).write(
            {
                "partner_id": partner.id,
                "partner_invoice_id": partner.id,
                "partner_shipping_id": partner.id,
            }
        )

    def _auto_order_register_customer(self, vat, name="", phone="", email=""):
        self.ensure_one()
        order = self._auto_order_saved_order()
        if not order:
            return {"error": _("The order is no longer available.")}
        vat = (vat or "").strip()
        if not self._auto_order_normalize_vat(vat):
            return {"error": _("Please fill in the RIF.")}
        partner = self._auto_order_find_partner_by_vat(vat)
        ctx = self._auto_order_cart_context()
        try:
            if partner:
                self._auto_order_assign_order_partner(order, partner)
                return {"ok": True, "orderName": order.name}
            name = (name or "").strip()
            phone = (phone or "").strip()
            email = (email or "").strip()
            if not name or not phone or not email:
                return {"error": _("Please fill in name, phone and email.")}
            if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
                return {"error": _("Enter a valid email.")}
            values = {
                "name": name,
                "vat": vat,
                "phone": phone,
                "email": email,
                "company_id": self.company_id.id,
                "customer_rank": 1,
            }
            country = self.env.ref("base.ve", raise_if_not_found=False)
            if country:
                values["country_id"] = country.id
            partner = (
                self.env["res.partner"]
                .with_user(SUPERUSER_ID)
                .with_context(**ctx)
                .create(values)
            )
            self._auto_order_assign_order_partner(order, partner)
        except UserError as err:
            return {"error": err.args[0] if err.args else str(err)}
        return {"ok": True, "orderName": order.name}

    def _auto_order_finish(self):
        if request:
            request.session.pop("auto_order_checkout_id", None)
        return {"ok": True, "cart": self._get_auto_order_empty_cart()}

    def _get_auto_order_empty_cart(self):
        self.ensure_one()
        company_currency = self.company_id.currency_id
        pricelist = self._get_auto_order_pricelist()
        zero_company = format_amount(self.env, 0.0, company_currency)
        zero_pricelist = format_amount(self.env, 0.0, pricelist.currency_id)
        return {
            "order_id": False,
            "line_count": 0,
            "lines": [],
            "same_currency": company_currency == pricelist.currency_id,
            "rateLabel": self._get_auto_order_rate_label(
                company_currency, pricelist.currency_id
            ),
            "company_currency_name": company_currency.name,
            "pricelist_currency_name": pricelist.currency_id.name,
            "amount_company_untaxed_formatted": zero_company,
            "amount_company_taxed_formatted": zero_company,
            "amount_pricelist_untaxed_formatted": zero_pricelist,
            "amount_pricelist_taxed_formatted": zero_pricelist,
        }

    def _get_auto_order_cart_data(self):
        self.ensure_one()
        order = self._get_auto_order_session_order()
        if not order or not order.sudo().cart_quantity:
            return self._get_auto_order_empty_cart()
        company = self.company_id
        company_currency = company.currency_id
        order_currency = order.currency_id
        date = fields.Date.context_today(self)
        amount_untaxed_company = order_currency._convert(
            order.amount_untaxed,
            company_currency,
            company,
            date,
        )
        amount_total_company = order_currency._convert(
            order.amount_total,
            company_currency,
            company,
            date,
        )
        lines = []
        for line in order._get_non_delivery_lines():
            line_untaxed_company = order_currency._convert(
                line.price_subtotal,
                company_currency,
                company,
                date,
            )
            line_taxed_company = order_currency._convert(
                line.price_total,
                company_currency,
                company,
                date,
            )
            lines.append(
                {
                    "id": line.id,
                    "product_id": line.product_id.id,
                    "name": line.name_short or line.product_id.display_name,
                    "quantity": line.product_uom_qty,
                    "uom_name": line.product_uom.name,
                    "image_url": "/web/image/product.product/%s/image_128"
                    % line.product_id.id,
                    "price_company_untaxed_formatted": format_amount(
                        self.env, line_untaxed_company, company_currency
                    ),
                    "price_company_taxed_formatted": format_amount(
                        self.env, line_taxed_company, company_currency
                    ),
                    "price_pricelist_untaxed_formatted": format_amount(
                        self.env, line.price_subtotal, order_currency
                    ),
                    "price_pricelist_taxed_formatted": format_amount(
                        self.env, line.price_total, order_currency
                    ),
                }
            )
        return {
            "order_id": order.id,
            "line_count": int(order.with_user(SUPERUSER_ID).cart_quantity),
            "lines": lines,
            "same_currency": company_currency == order_currency,
            "rateLabel": self._get_auto_order_rate_label(
                company_currency, order_currency
            ),
            "company_currency_name": company_currency.name,
            "pricelist_currency_name": order_currency.name,
            "amount_company_untaxed_formatted": format_amount(
                self.env, amount_untaxed_company, company_currency
            ),
            "amount_company_taxed_formatted": format_amount(
                self.env, amount_total_company, company_currency
            ),
            "amount_pricelist_untaxed_formatted": format_amount(
                self.env, order.amount_untaxed, order_currency
            ),
            "amount_pricelist_taxed_formatted": format_amount(
                self.env, order.amount_total, order_currency
            ),
        }
