# -*- coding: utf-8 -*-
import base64
import io
import subprocess

from markupsafe import Markup
from PIL import Image

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools.misc import find_in_path

LOGO_ORIGIN = (81, 212)
LOGO_SIZE = (48, 48)


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
    def _decode_image_bytes(self, value):
        if not value:
            return b""
        if isinstance(value, str):
            value = value.encode("ascii", "ignore")
        if value[:8] == b"\x89PNG\r\n\x1a\n" or value[:3] == b"\xff\xd8\xff":
            return value
        if value[:4] == b"RIFF" and value[8:12] == b"WEBP":
            return value
        if value[:4] == b"GIF8":
            return value
        try:
            decoded = base64.b64decode(value, validate=False)
        except (ValueError, TypeError):
            return value
        return decoded or value

    @api.model
    def _open_webp(self, raw):
        convert = find_in_path("convert")
        if not convert:
            return None
        try:
            proc = subprocess.run(
                [convert, "webp:-", "png:-"],
                input=raw,
                capture_output=True,
                check=False,
                timeout=15,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if proc.returncode != 0 or not proc.stdout:
            return None
        try:
            image = Image.open(io.BytesIO(proc.stdout))
            image.load()
            return image
        except (OSError, ValueError):
            return None

    @api.model
    def _open_image(self, raw):
        if not raw:
            return None
        try:
            image = Image.open(io.BytesIO(raw))
            image.load()
            return image
        except (OSError, ValueError):
            pass
        if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
            return self._open_webp(raw)
        return None

    @api.model
    def _iter_company_logo_binaries(self, company):
        partner = company.partner_id
        for value in (
            company.logo,
            company.logo_web,
            partner.image_512,
            partner.image_256,
            partner.image_128,
        ):
            raw = self._decode_image_bytes(value)
            if raw:
                yield raw

    @api.model
    def _image_to_zpl_gfa(self, image, origin=LOGO_ORIGIN, size=LOGO_SIZE):
        if image.mode in ("RGBA", "LA"):
            background = Image.new("RGBA", image.size, (255, 255, 255, 255))
            image = Image.alpha_composite(background, image.convert("RGBA"))
        image = image.convert("L")
        width, height = size
        image.thumbnail((width, height), Image.Resampling.LANCZOS)
        canvas = Image.new("L", (width, height), 255)
        offset_x = (width - image.width) // 2
        offset_y = (height - image.height) // 2
        canvas.paste(image, (offset_x, offset_y))
        bw = canvas.convert("1")

        bytes_per_row = (width + 7) // 8
        padded_width = bytes_per_row * 8
        rows = []
        for pos_y in range(height):
            byte = 0
            bit_index = 0
            row = bytearray()
            for pos_x in range(padded_width):
                bit = 0
                if pos_x < width:
                    pixel = bw.getpixel((pos_x, pos_y))
                    bit = 1 if pixel == 0 else 0
                byte = (byte << 1) | bit
                bit_index += 1
                if bit_index == 8:
                    row.append(byte)
                    byte = 0
                    bit_index = 0
            rows.append(row)
        payload = b"".join(rows)
        if not payload or not any(payload):
            return ""
        return (
            "^FO%d,%d^GFA,%d,%d,%d,%s^FS"
            % (
                origin[0],
                origin[1],
                len(payload),
                len(payload),
                bytes_per_row,
                payload.hex().upper(),
            )
        )

    @api.model
    def _logo_to_zpl_gfa(self, image_value):
        image = self._open_image(self._decode_image_bytes(image_value))
        if image is None:
            return ""
        return self._image_to_zpl_gfa(image)

    @api.model
    def _label_logo_gfa(self, company=None):
        company = company or self.env.company
        if company.qr_label_logo:
            gfa = self._logo_to_zpl_gfa(company.qr_label_logo)
            if gfa:
                return gfa
        if company.uses_default_logo:
            return ""
        for raw in self._iter_company_logo_binaries(company):
            image = self._open_image(raw)
            if image is None:
                continue
            gfa = self._image_to_zpl_gfa(image)
            if gfa:
                return gfa
        return ""

    @api.model
    def _build_label_zpl(self, product, mode, footer=None):
        qr_payload = self._get_qr_payload(product, mode)
        product_name = self._zpl_wrap_name(product.name or product.display_name)
        code = self._zpl_sanitize(product.default_code or product.qr_code or "")
        footer_text = self._zpl_sanitize(footer or product.env.company.name or "")
        logo_gfa = self._label_logo_gfa(product.env.company)

        parts = [
            "^XA\n",
            "^CI28\n",
            "^PW600\n",
            "^LL300\n",
            "^LH0,0\n",
            "^LS0\n",
            "\n",
            "^FO81,25\n",
            "^BQN,2,4\n",
            "^FDQA,%s^FS\n" % qr_payload,
            "\n",
            "^FO280,20\n",
            "^A0N,14,14\n",
            "^FDPRODUCTO^FS\n",
            "\n",
            "^FO280,38\n",
            "^A0N,18,18\n",
            "^FB255,3,7,L,0\n",
            "^FD%s^FS\n" % product_name,
            "\n",
            "^FO280,125\n",
            "^A0N,14,14\n",
            "^FDCODIGO^FS\n",
            "\n",
            "^FO280,145\n",
            "^A0N,24,24\n",
            "^FB305,1,0,L,0\n",
            "^FD%s^FS\n" % code,
        ]
        if logo_gfa:
            parts.extend(["\n", logo_gfa, "\n"])
        if footer_text:
            parts.extend(
                [
                    "\n",
                    "^FO81,272\n",
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
