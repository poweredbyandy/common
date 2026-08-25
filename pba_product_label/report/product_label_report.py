# -*- coding: utf-8 -*-
import base64
import io
import subprocess

from markupsafe import Markup
from PIL import Image

from odoo import models
from odoo.tools.misc import find_in_path

LOGO_ORIGIN = (100, 30)
LOGO_SIZE = (64, 64)


class ReportPbaProductLabel(models.AbstractModel):
    _name = "report.pba_product_label.label_product_product_view"
    _inherit = "report.stock.label_product_product_view"
    _description = "PBA Product Label (ZPL)"

    def _zpl_text(self, value):
        text = "" if value is None else str(value)
        return Markup(
            text.replace("^", " ").replace("~", " ").replace("\\", " ")
        )

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

    def _logo_to_zpl_gfa(self, image_b64, origin=LOGO_ORIGIN, size=LOGO_SIZE):
        image = self._open_image(self._decode_image_bytes(image_b64))
        if image is None:
            return ""
        return self._image_to_zpl_gfa(image, origin=origin, size=size)

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

    def _company_logo_gfa(self, company=None):
        company = company or self.env.company
        for raw in self._iter_company_logo_binaries(company):
            image = self._open_image(raw)
            if image is None:
                continue
            gfa = self._image_to_zpl_gfa(image)
            if gfa:
                return gfa
        return ""

    def _get_report_values(self, docids, data):
        data = super()._get_report_values(docids, data)
        data["company"] = self.env.company
        data["zpl_text"] = self._zpl_text
        data["company_logo_gfa"] = Markup(self._company_logo_gfa(self.env.company))
        return data
