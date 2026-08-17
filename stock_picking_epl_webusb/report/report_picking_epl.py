# -*- coding: utf-8 -*-

import base64
import io
import re
import unicodedata

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.exceptions import UserError

DOTS_W = 812
FORM_H = 812
GAP_DOTS = 24
LF = "\n"
LOGO_MAX_W = 340
LOGO_MAX_H = 150
LOGO_X = 20
LOGO_Y = 6
BC_PKG_MAX_LEN = 22
QR_GAP_DOTS = 14
FONT_CLIENT = 4
FONT_BULTO = 5
CLIENT_NAME_LINE_STEP = 48
CLIENT_AFTER_NAMES_GAP = 12
CLIENT_NAME_CHARS_PER_LINE = 50
CLIENT_MAX_NAME_LINES = 3
CLIENT_NAME_MAX_CHARS = 160
BULTO_TEXT_Y_OFF = 128
BARCODE_Y_AFTER_BULTO = 60
BC_LINE_HEIGHT = 84
CLIENT_VAT_FIRST_LINE_MAX_Y = (
    FORM_H - BC_LINE_HEIGHT - BULTO_TEXT_Y_OFF - BARCODE_Y_AFTER_BULTO
)
QR_MIN_SIDE = 260
QR_MAX_SIDE_CAP = 480
FONT2_CHAR_DOTS = 10
RIGHT_MARGIN = 8
INV_SALE_X = 520
INV_SALE_MAX_CHARS = 28
INV_Y = 34
SALE_ORDER_Y = 72


def _epl_ascii(value, max_len=200):
    if value is False or value is None:
        return ""
    text = str(value)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\x20-\x7e]", "", text)
    text = text.replace('"', '""')
    return text[:max_len]


def _epl_field(value, default="-"):
    s = _epl_ascii(value) if value not in (False, None) else ""
    if not s:
        s = _epl_ascii(default) or "-"
    return s if s else "-"


def _split_fixed(text, width, count):
    t = _epl_ascii(text, width * count + 50).strip()
    if not t:
        return ["-"] * count
    out = []
    for i in range(count):
        chunk = t[i * width : (i + 1) * width].strip()
        out.append(chunk if chunk else "-")
    return out


CODE39_CHARS = set("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%+-./")


def _epl_code39_payload(text, max_len=40):
    t = _epl_ascii(text or "", max_len * 2).upper()
    out = []
    for c in t:
        if c in CODE39_CHARS:
            out.append(c)
        elif c == "-":
            out.append("-")
        else:
            out.append(" ")
    s = "".join(out).strip()
    s = re.sub(r"\s+", " ", s)
    return (s[:max_len] if s else "X").strip() or "X"


def _binary_image_field_to_bytes(logo_field):
    if not logo_field:
        return None
    if isinstance(logo_field, memoryview):
        logo_field = logo_field.tobytes()
    if isinstance(logo_field, str):
        return base64.b64decode(logo_field, validate=False)
    if isinstance(logo_field, bytes):
        if logo_field.startswith(
            (b"\xff\xd8", b"\x89PNG", b"GIF8", b"BM", b"RIFF", b"\x00\x00\x01\x00")
        ):
            return logo_field
        try:
            return base64.b64decode(logo_field, validate=True)
        except Exception:
            return logo_field
    return None


def _gw_ink_score(bmp):
    return sum(bin(byte).count("1") for byte in bmp)


def _pack_epl_gw_bitmap(im_l, invert=False):
    w, h = im_l.size
    w_bytes = (w + 7) // 8
    out = bytearray()
    px = im_l.load()
    for yy in range(h):
        row = bytearray(w_bytes)
        for xx in range(w):
            lum = px[xx, yy]
            black = lum >= 128 if invert else lum < 128
            if black:
                row[xx // 8] |= 1 << (7 - (xx % 8))
        out.extend(row)
    return w, h, w_bytes, bytes(out)


class ReportPickingEpl(models.AbstractModel):
    _name = "report.stock_picking_epl_webusb.report_picking_epl"
    _description = "Etiquetas de paquetes EPL (albarán)"

    @api.model
    def _picking_packages_sequence(self, picking):
        packages = picking.move_line_ids.result_package_id
        packages = packages.filtered(lambda p: p)
        return packages.sorted(lambda p: (p.name or "", p.id))

    @api.model
    def _epl_center_x(self, text, label_width=812, char_dots=11):
        t = _epl_ascii(text or "", 120).strip() or "-"
        w = min(len(t) * char_dots, label_width - 40)
        return max(20, (label_width - w) // 2)

    @api.model
    def _print_datetime_str(self):
        now = fields.Datetime.now()
        ts = fields.Datetime.context_timestamp(self.env.user, now)
        return ts.strftime("%d/%m/%Y %H:%M")

    @api.model
    def _invoice_ref(self, picking):
        if "sale_id" in picking._fields and picking.sale_id:
            invs = picking.sale_id.invoice_ids.filtered(
                lambda m: m.state == "posted" and m.move_type == "out_invoice"
            )
            if invs:
                invs = invs.sorted(
                    key=lambda m: (m.invoice_date or m.date, m.id),
                    reverse=True,
                )
                m0 = invs[0]
                return m0.name or m0.payment_reference or ""
        if "purchase_id" in picking._fields and picking.purchase_id:
            invs = picking.purchase_id.invoice_ids.filtered(
                lambda m: m.state == "posted" and m.move_type == "in_invoice"
            )
            if invs:
                invs = invs.sorted(
                    key=lambda m: (m.invoice_date or m.date, m.id),
                    reverse=True,
                )
                m0 = invs[0]
                return m0.name or m0.payment_reference or ""
        return picking.origin or ""

    @api.model
    def _sale_order_ref(self, picking):
        if "sale_id" in picking._fields and picking.sale_id:
            return picking.sale_id.name or picking.sale_id.display_name or ""
        return ""

    @api.model
    def _company_header_lines(self, company, company_p):
        l1 = _epl_field(company_p.street or "-", "-")[:52]
        sub = " ".join(
            p
            for p in [
                company_p.street2,
                company_p.city,
                company_p.state_id.name if company_p.state_id else "",
            ]
            if p
        ) or "-"
        l2 = _epl_field(sub, "-")[:52]
        l3 = _epl_field(
            "Telf. %s" % (company_p.phone or company_p.mobile or "-"),
            "Telf. -",
        )[:52]
        return l1, l2, l3

    @api.model
    def _partner_phone(self, partner):
        if not partner:
            return False
        commercial_partner = partner.commercial_partner_id
        candidates = [partner.phone, partner.mobile]
        if commercial_partner != partner:
            candidates.extend([commercial_partner.phone, commercial_partner.mobile])
        for value in candidates:
            if value and value.strip():
                return value.strip()
        return False

    @api.model
    def _label_plain_lines(self, picking, package, index, total):
        company = picking.company_id
        company_p = company.partner_id if company else self.env["res.partner"].browse()
        partner = picking.partner_id or self.env["res.partner"].browse()
        l1, l2, l3 = self._company_header_lines(company, company_p)
        com_vat = _epl_field(company_p.vat or company.vat or "-")
        com_name = _epl_field(company.name or company_p.name or "-")[:52]
        print_dt = self._print_datetime_str()
        inv = _epl_field(self._invoice_ref(picking), "-")[:INV_SALE_MAX_CHARS]
        sale = _epl_field(self._sale_order_ref(picking), "-")[:INV_SALE_MAX_CHARS]
        layout = self._layout_company_block(company, company_p, for_text_report=True)
        y_client = layout["y_addr"] + 88
        max_c_lines = self._max_client_name_lines(y_client)
        c_lines = self._split_client_name_lines(partner, max_lines=max_c_lines)
        cname = "\n".join(c_lines)[:170]
        pvat = _epl_field(partner.vat or "-")[:40]
        d1, d2 = self._partner_dest_lines(partner)
        tel = _epl_field(self._partner_phone(partner) or "-")[:40]
        pkg_url = self._package_open_url(package) or self._picking_open_url(picking)
        return [
            com_name,
            com_vat,
            print_dt,
            inv,
            sale,
            l1,
            l2,
            l3,
            cname,
            pvat,
            d1,
            d2,
            "Tel: %s" % tel,
            "Bulto %s de %s" % (int(index), int(total)),
            _epl_field(pkg_url, "-")[:200],
        ]

    @api.model
    def _partner_dest_lines(self, partner):
        parts = [
            partner.street,
            partner.street2,
            partner.city,
            partner.state_id.name if partner.state_id else "",
        ]
        raw = " ".join(p for p in parts if p) or "-"
        return _split_fixed(raw, 50, 2)

    @api.model
    def _split_company_display_name(self, company, company_p, line_width=46):
        name = _epl_field(company.name or company_p.name or "-", "-")[:92]
        if len(name) <= line_width:
            return name, ""
        return name[:line_width].rstrip(), name[line_width : line_width * 2].strip()

    @api.model
    def _epl_right_align_x(self, text, font_dots, min_x):
        t = _epl_ascii(text or "", 80).strip() or "-"
        for max_len in (28, 24, 20, 16, 12, 8):
            tt = t[:max_len]
            x = DOTS_W - RIGHT_MARGIN - len(tt) * font_dots
            if x >= min_x:
                return x, tt
        tt = t[:6]
        return min_x, tt

    @api.model
    def _max_client_name_lines(self, y_client):
        avail = CLIENT_VAT_FIRST_LINE_MAX_Y - CLIENT_AFTER_NAMES_GAP - int(y_client)
        if avail < CLIENT_NAME_LINE_STEP:
            return 1
        n = int(avail // CLIENT_NAME_LINE_STEP)
        return max(1, min(CLIENT_MAX_NAME_LINES, n))

    @api.model
    def _split_client_name_lines(self, partner, chars_per_line=None, max_lines=None):
        chars_per_line = chars_per_line or CLIENT_NAME_CHARS_PER_LINE
        max_lines = max_lines or CLIENT_MAX_NAME_LINES
        raw = (_epl_field(partner.name or "-", "-")[:CLIENT_NAME_MAX_CHARS]).strip() or "-"
        lines = []
        t = raw
        while t and len(lines) < max_lines:
            if len(t) <= chars_per_line:
                lines.append(t.rstrip())
                t = ""
                break
            window = t[:chars_per_line]
            sp = window.rfind(" ")
            if sp > chars_per_line // 3:
                cut = sp + 1
            else:
                cut = chars_per_line
            piece = t[:cut].rstrip()
            if not piece:
                cut = chars_per_line
                piece = t[:cut].rstrip()
            piece = piece[:chars_per_line]
            lines.append(piece.rstrip())
            t = t[cut:].lstrip()
        if t and lines:
            combined = (lines[-1] + " " + t).strip()
            lines[-1] = (
                combined[: max(1, chars_per_line - 3)].rstrip() + "..."
            )
        if not lines:
            lines = ["-"]
        return lines[:max_lines]

    @api.model
    def _company_logo_gw_block(self, company):
        try:
            from PIL import Image
        except ImportError:
            return None
        if not company:
            return None
        raw = _binary_image_field_to_bytes(company.logo)
        if not raw:
            return None
        try:
            im = Image.open(io.BytesIO(raw))
        except Exception:
            return None
        if im.mode != "RGBA":
            im = im.convert("RGBA")
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        bg = Image.alpha_composite(bg, im)
        im = bg.convert("RGB")
        im.thumbnail((LOGO_MAX_W, LOGO_MAX_H), Image.Resampling.LANCZOS)
        tw, th = im.size
        canvas = Image.new("RGB", (LOGO_MAX_W, LOGO_MAX_H), (255, 255, 255))
        ox = (LOGO_MAX_W - tw) // 2
        oy = (LOGO_MAX_H - th) // 2
        canvas.paste(im, (ox, oy))
        im_l = canvas.convert("L")
        _w, _h, w_bytes, bmp0 = _pack_epl_gw_bitmap(im_l, invert=False)
        _w2, _h2, w_bytes2, bmp1 = _pack_epl_gw_bitmap(im_l, invert=True)
        bmp = bmp0
        if w_bytes2 == w_bytes and _gw_ink_score(bmp1) > _gw_ink_score(bmp0):
            bmp = bmp1
        header = ("GW%d,%d,%d,%d\n" % (LOGO_X, LOGO_Y, w_bytes, im_l.size[1])).encode(
            "ascii"
        )
        return header + bmp

    @api.model
    def _package_open_url(self, package):
        if not package:
            return ""
        base = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "") or ""
        base = base.rstrip("/")
        if not base:
            return ""
        return "%s/web#id=%s&model=stock.quant.package&view_type=form" % (
            base,
            int(package.id),
        )

    @api.model
    def _picking_open_url(self, picking):
        if not picking:
            return ""
        base = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "") or ""
        base = base.rstrip("/")
        if not base:
            return ""
        return "%s/web#id=%s&model=stock.picking&view_type=form" % (base, int(picking.id))

    @api.model
    def _picking_label_jobs(self, picking):
        packages = self._picking_packages_sequence(picking)
        if packages:
            total = len(packages)
            return [(p, i, total) for i, p in enumerate(packages, start=1)]
        n = int(picking.dispatch_bultos_manual or 0)
        if n <= 0:
            return None
        empty = self.env["stock.quant.package"].browse()
        return [(empty, i, n) for i in range(1, n + 1)]

    @api.model
    def _qr_raster_gw_block(self, text, gx, gy, max_side=400):
        try:
            import qrcode
            from PIL import Image
        except ImportError:
            return None
        text = (text or "").strip()
        if not text:
            return None
        text = _epl_ascii(text, max_len=1500)
        if not text:
            return None
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=5,
            border=2,
        )
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("L")
        w0, h0 = img.size
        if max(w0, h0) > max_side:
            scale = max_side / float(max(w0, h0))
            nw = max(8, int(w0 * scale))
            nh = max(8, int(h0 * scale))
            img = img.resize((nw, nh), Image.Resampling.NEAREST)
        w, h = img.size
        w_pad = ((w + 7) // 8) * 8
        if w_pad != w:
            canvas = Image.new("L", (w_pad, h), 255)
            canvas.paste(img, (0, 0))
            img = canvas
        _w, _h, w_bytes, bmp0 = _pack_epl_gw_bitmap(img, invert=False)
        _w2, _h2, w_bytes2, bmp1 = _pack_epl_gw_bitmap(img, invert=True)
        bmp = bmp0
        if w_bytes2 == w_bytes and _gw_ink_score(bmp1) > _gw_ink_score(bmp0):
            bmp = bmp1
        header = ("GW%d,%d,%d,%d\n" % (gx, gy, w_bytes, img.size[1])).encode("ascii")
        return header + bmp

    @api.model
    def _epl_qr_fallback_b_line(self, x, y, url):
        u = _epl_ascii(url, max_len=400)
        if not u:
            return ""
        u = u.replace("\\", "\\\\").replace('"', '\\"').replace("/", "\\/")
        return f'b{x},{y},Q,s8,m2,"{u}"'

    @api.model
    def _epl_label_tail_segments(
        self,
        picking,
        package,
        index,
        total,
        tx,
        ty_n1,
        ty_n2,
        ty_vat,
        y_addr,
    ):
        company = picking.company_id
        company_p = company.partner_id if company else self.env["res.partner"].browse()
        partner = picking.partner_id or self.env["res.partner"].browse()
        com_vat = _epl_field(company_p.vat or company.vat or "-")
        com_n1, com_n2 = self._split_company_display_name(company, company_p)
        l1, l2, l3 = self._company_header_lines(company, company_p)
        print_dt = _epl_field(self._print_datetime_str(), "-")[:22]
        inv = _epl_field(self._invoice_ref(picking), "-")[:INV_SALE_MAX_CHARS]
        sale = _epl_field(self._sale_order_ref(picking), "-")[:INV_SALE_MAX_CHARS]
        min_rx = max(20, tx + 10)
        x_dt, t_dt = self._epl_right_align_x(print_dt, FONT2_CHAR_DOTS, min_rx)
        x_inv = max(min_rx, INV_SALE_X)
        t_inv = inv
        x_so = x_inv
        t_so = sale
        pvat = _epl_field(partner.vat or "-", "-")[:36]
        d1, d2 = self._partner_dest_lines(partner)
        tel = _epl_field(self._partner_phone(partner) or "-", "-")[:36]
        idx_s = str(int(index))
        tot_s = str(int(total))
        bulto_txt = "BULTO %s DE %s" % (idx_s, tot_s)
        if package:
            pname = package.display_name or package.name or "PKG"
        else:
            pname = picking._epl_label_scan_text()
        pkg_bc = _epl_code39_payload(pname, max_len=BC_PKG_MAX_LEN)
        lines = [
            f'A{tx},{ty_n1},0,3,1,1,N,"{com_n1}"',
        ]
        if com_n2:
            lines.append(f'A{tx},{ty_n2},0,3,1,1,N,"{com_n2}"')
        lines.extend(
            [
                f'A{tx},{ty_vat},0,2,1,1,N,"{com_vat}"',
                f'A{x_dt},10,0,2,1,1,N,"{t_dt}"',
                f'A{x_inv},{INV_Y},0,2,1,1,N,"{t_inv}"',
                f'A{x_so},{SALE_ORDER_Y},0,2,1,1,N,"{t_so}"',
                f'A{self._epl_center_x(l1)},{y_addr},0,2,1,1,N,"{l1}"',
                f'A{self._epl_center_x(l2)},{y_addr + 24},0,2,1,1,N,"{l2}"',
                f'A{self._epl_center_x(l3)},{y_addr + 48},0,2,1,1,N,"{l3}"',
            ]
        )
        y_client = y_addr + 88
        max_c_lines = self._max_client_name_lines(y_client)
        c_lines = self._split_client_name_lines(partner, max_lines=max_c_lines)
        for i, cn in enumerate(c_lines):
            yy = y_client + i * CLIENT_NAME_LINE_STEP
            tcn = cn[:CLIENT_NAME_CHARS_PER_LINE]
            lines.append(f'A40,{yy},0,{FONT_CLIENT},1,1,N,"{tcn}"')
        ncn = len(c_lines)
        y_vat = y_client + ncn * CLIENT_NAME_LINE_STEP + CLIENT_AFTER_NAMES_GAP
        lines.extend(
            [
                f'A40,{y_vat},0,2,1,1,N,"{pvat}"',
                f'A40,{y_vat + 34},0,2,1,1,N,"{d1}"',
                f'A40,{y_vat + 58},0,2,1,1,N,"{d2}"',
                f'A40,{y_vat + 92},0,2,1,1,N,"Telf. {tel}"',
                f'A40,{y_vat + BULTO_TEXT_Y_OFF},0,{FONT_BULTO},1,1,N,"{bulto_txt}"',
            ]
        )
        y_bar = y_vat + BULTO_TEXT_Y_OFF + BARCODE_Y_AFTER_BULTO
        return {"main_lines": lines, "y_bar": y_bar, "pkg_bc": pkg_bc}

    @api.model
    def _epl_label_ascii_tail(
        self,
        picking,
        package,
        index,
        total,
        tx,
        ty_n1,
        ty_n2,
        ty_vat,
        y_addr,
    ):
        seg = self._epl_label_tail_segments(
            picking,
            package,
            index,
            total,
            tx,
            ty_n1,
            ty_n2,
            ty_vat,
            y_addr,
        )
        bc = f'B40,{seg["y_bar"]},0,3,2,4,{BC_LINE_HEIGHT},B,"{seg["pkg_bc"]}"'
        return LF.join(seg["main_lines"] + [bc, "P1"]) + LF

    @api.model
    def _layout_company_block(self, company, company_p, for_text_report=False):
        _, com_n2 = self._split_company_display_name(company, company_p)
        raw = _binary_image_field_to_bytes(company.logo) if company else None
        has_image = bool(raw)
        gw_block = None
        if has_image and not for_text_report:
            gw_block = self._company_logo_gw_block(company)
        if has_image:
            tx = LOGO_X + LOGO_MAX_W + 12
            ty_n1 = 10
            if com_n2:
                ty_n2 = 34
                ty_vat = 58
            else:
                ty_n2 = 0
                ty_vat = 40
            y_addr = max(LOGO_Y + LOGO_MAX_H, ty_vat + 22) + 12
        else:
            tx = 20
            ty_n1 = 48
            if com_n2:
                ty_n2 = 76
                ty_vat = 106
            else:
                ty_n2 = 0
                ty_vat = 82
            y_addr = ty_vat + 28
        return {
            "gw_block": gw_block,
            "has_image_logo": has_image,
            "tx": tx,
            "ty_n1": ty_n1,
            "ty_n2": ty_n2,
            "ty_vat": ty_vat,
            "y_addr": y_addr,
            "com_n2": com_n2,
        }

    @api.model
    def _build_epl_package_label(self, picking, package, index, total):
        company = picking.company_id
        company_p = company.partner_id if company else self.env["res.partner"].browse()
        layout = self._layout_company_block(company, company_p, for_text_report=True)
        prefix = LF.join(
            [
                "N",
                f"q{DOTS_W}",
                f"Q{FORM_H},{GAP_DOTS}",
                "ZB",
                "rN",
                "D15",
            ]
        )
        ty_n2_val = layout["ty_n2"] if layout["com_n2"] else layout["ty_n1"]
        tail = self._epl_label_ascii_tail(
            picking,
            package,
            index,
            total,
            layout["tx"],
            layout["ty_n1"],
            ty_n2_val,
            layout["ty_vat"],
            layout["y_addr"],
        )
        return prefix + LF + tail

    @api.model
    def _build_epl_package_label_bytes(self, picking, package, index, total):
        company = picking.company_id
        company_p = company.partner_id if company else self.env["res.partner"].browse()
        layout = self._layout_company_block(company, company_p, for_text_report=False)
        head = (
            "N\n"
            + f"q{DOTS_W}\n"
            + f"Q{FORM_H},{GAP_DOTS}\n"
            + "ZB\n"
            + "rN\n"
            + "D15\n"
        ).encode("ascii")
        parts = [head]
        if layout["gw_block"]:
            parts.append(layout["gw_block"])
        ty_n2_val = layout["ty_n2"] if layout["com_n2"] else layout["ty_n1"]
        seg = self._epl_label_tail_segments(
            picking,
            package,
            index,
            total,
            layout["tx"],
            layout["ty_n1"],
            ty_n2_val,
            layout["ty_vat"],
            layout["y_addr"],
        )
        main_b = (LF.join(seg["main_lines"]) + LF).encode("ascii")
        bc_b = (
            f'B40,{seg["y_bar"]},0,3,2,4,{BC_LINE_HEIGHT},B,"{seg["pkg_bc"]}"\n'
        ).encode("ascii")
        url = self._package_open_url(package) or self._picking_open_url(picking)
        qr_b = b""
        if url:
            pkg_bc = seg["pkg_bc"]
            est_bc_w = min(340, 52 + len(pkg_bc) * 19)
            qx = 40 + est_bc_w + QR_GAP_DOTS
            yb = seg["y_bar"]
            room_w = DOTS_W - qx - 8
            room_h = FORM_H - yb - 24
            max_q = min(QR_MAX_SIDE_CAP, room_w, room_h)
            max_q = max(QR_MIN_SIDE, max_q)
            max_q = min(max_q, room_w, room_h)
            qy = yb + max(0, (BC_LINE_HEIGHT - max_q) // 2)
            qr_b = self._qr_raster_gw_block(url, qx, qy, max_side=max_q) or b""
            if not qr_b:
                qline = self._epl_qr_fallback_b_line(qx, qy, url)
                if qline:
                    qr_b = (qline + "\n").encode("ascii")
        parts.append(main_b + bc_b + qr_b + b"P1\n")
        return b"".join(parts)

    @api.model
    def _build_epl_body(self, pickings):
        chunks = []
        for picking in pickings:
            jobs = self._picking_label_jobs(picking)
            if not jobs:
                raise UserError(
                    _(
                        "El albarán %s no tiene paquetes destino (result_package_id). "
                        "Indique bultos en el campo «Bultos (sin empaquetar)» o empaquete las líneas."
                    )
                    % (picking.display_name,)
                )
            for package, index, total in jobs:
                chunks.append(
                    self._build_epl_package_label(picking, package, index, total)
                )
        return "".join(chunks)

    @api.model
    def _render_epl_webusb_binary_body(self, pickings):
        out = bytearray()
        for picking in pickings:
            jobs = self._picking_label_jobs(picking)
            if not jobs:
                raise UserError(
                    _(
                        "El albarán %s no tiene paquetes destino (result_package_id). "
                        "Indique bultos en el campo «Bultos (sin empaquetar)» o empaquete las líneas."
                    )
                    % (picking.display_name,)
                )
            for package, index, total in jobs:
                out.extend(
                    self._build_epl_package_label_bytes(
                        picking, package, index, total
                    )
                )
        return bytes(out)

    @api.model
    def _get_report_values(self, docids, data=None):
        if not docids:
            raise UserError(_("No se indicaron albaranes para el informe EPL."))
        pickings = self.env["stock.picking"].browse(docids)
        if not pickings:
            raise UserError(_("No se encontraron albaranes para el informe EPL."))
        epl_body = self._build_epl_body(pickings)
        return {
            "doc_ids": docids,
            "doc_model": "stock.picking",
            "docs": pickings,
            "epl_body": Markup(epl_body),
        }