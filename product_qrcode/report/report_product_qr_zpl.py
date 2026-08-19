# -*- coding: utf-8 -*-

from markupsafe import Markup

from odoo import _, api, models
from odoo.exceptions import UserError


class ReportProductQrZpl(models.AbstractModel):
    _name = "report.product_qrcode.report_product_qr_zpl_document"
    _description = "Product QR labels (ZPL)"

    @api.model
    def _zpl_sanitize(self, text):
        if not text:
            return ""
        return str(text).replace("^", " ").replace("~", " ").replace("\\", " ")

    @api.model
    def _zpl_wrap_name(self, name, max_chars=26, max_lines=3):
        name = self._zpl_sanitize(name)
        words = name.split()
        lines = []
        current = ""
        for word in words:
            candidate = "%s %s" % (current, word) if current else word
            if len(candidate) <= max_chars:
                current = candidate
                continue
            if current:
                lines.append(current)
            if len(lines) >= max_lines:
                return r"\&".join(lines[:max_lines])
            current = word[:max_chars]
        if current and len(lines) < max_lines:
            lines.append(current)
        return r"\&".join(lines[:max_lines])

    @api.model
    def _get_qr_payload(self, product, mode):
        if mode == "portal":
            url = getattr(product, "portal_qr_url", False)
            if not url:
                raise UserError(
                    _("Portal QR URL is not available for %s.")
                    % (product.display_name,)
                )
            return url
        code = product.qr_code or product._get_qr_code_value()
        if not code:
            raise UserError(
                _("Product QR code is not available for %s.")
                % (product.display_name,)
            )
        return code

    @api.model
    def _build_label_zpl(self, product, mode, footer=None):
        qr_payload = self._get_qr_payload(product, mode)
        product_name = self._zpl_wrap_name(product.name or product.display_name)
        code = self._zpl_sanitize(product.default_code or product.qr_code or "")
        footer_text = self._zpl_sanitize(footer or product.env.company.name or "")

        parts = [
            "^XA\n",
            "^CI28\n",
            "^PW600\n",
            "^LL300\n",
            "^LH0,0\n",
            "^LS0\n",
            "\n",
            "^FO75,25\n",
            "^BQN,2,4\n",
            "^FDQA,%s^FS\n" % qr_payload,
            "\n",
            "^FO275,20\n",
            "^A0N,14,14\n",
            "^FDPRODUCTO^FS\n",
            "\n",
            "^FO275,38\n",
            "^A0N,18,18\n",
            "^FB255,3,7,L,0\n",
            "^FD%s^FS\n" % product_name,
            "\n",
            "^FO275,125\n",
            "^A0N,14,14\n",
            "^FDCODIGO^FS\n",
            "\n",
            "^FO275,145\n",
            "^A0N,24,24\n",
            "^FB305,1,0,L,0\n",
            "^FD%s^FS\n" % code,
        ]
        if footer_text:
            parts.extend(
                [
                    "\n",
                    "^FO75,272\n",
                    "^A0N,11,11\n",
                    "^FB450,1,0,C,0\n",
                    "^FD%s^FS\n" % footer_text,
                ]
            )
        parts.append("^XZ\n")
        return "".join(parts)

    @api.model
    def _iter_label_jobs(self, data):
        qty_map = data.get("quantity_by_product") or {}
        mode = data.get("zpl_qr_mode", "product")
        active_model = data.get("active_model")
        Product = self.env["product.product"].with_context(display_default_code=False)

        if active_model == "product.template":
            templates = self.env["product.template"].browse(
                [int(product_id) for product_id in qty_map]
            )
            for template in templates.sorted("name", reverse=True):
                quantity = qty_map.get(str(template.id), 1)
                for product in template.product_variant_ids:
                    yield product, quantity, mode
            return

        products = Product.search(
            [("id", "in", [int(product_id) for product_id in qty_map])],
            order="name desc",
        )
        for product in products:
            yield product, qty_map.get(str(product.id), 1), mode

    @api.model
    def _build_zpl_body(self, data):
        chunks = []
        for product, quantity, mode in self._iter_label_jobs(data):
            label = self._build_label_zpl(product, mode)
            for _unused in range(max(int(quantity), 0)):
                chunks.append(label)
        if not chunks:
            raise UserError(_("No product labels to print."))
        return "".join(chunks)

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        zpl_body = self._build_zpl_body(data)
        return {
            "doc_ids": docids,
            "doc_model": "product.product",
            "docs": self.env["product.product"],
            "zpl_body": Markup(zpl_body),
        }
