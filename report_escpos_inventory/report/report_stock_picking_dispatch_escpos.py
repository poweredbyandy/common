# -*- coding: utf-8 -*-

from markupsafe import Markup

from odoo import api, fields, models

LINE_WIDTH = 80

LETTER_HEIGHT_IN = 11.0
LETTER_MARGIN_TOP_IN = 0.5
LETTER_MARGIN_BOTTOM_IN = 0.5
MATRIX_LINE_SPACING_LPI = 6

TABLE_HEADER_LINES = 2
FOOTER_LINES_LAST = 5
FOOTER_LINES_CONTINUE = 2


def _matrix_letter_printable_lines():
    usable = LETTER_HEIGHT_IN - LETTER_MARGIN_TOP_IN - LETTER_MARGIN_BOTTOM_IN
    return max(1, int(usable * MATRIX_LINE_SPACING_LPI))


def _matrix_dispatch_reserved_lines(header_line_count, footer_lines):
    return header_line_count + TABLE_HEADER_LINES + footer_lines


def _matrix_dispatch_max_product_lines(header_line_count):
    page = _matrix_letter_printable_lines()
    reserved = _matrix_dispatch_reserved_lines(header_line_count, FOOTER_LINES_LAST)
    return max(1, page - reserved)

COL_IDX = 2
COL_REF = 16
COL_QTY = 6
COL_COD = 16
COL_BRAND = 10

_GAP = " "


def _nl(cmd_set):
    return "\r\n" if cmd_set == "esc_p_epson" else "\n"


def _control_bytes(cmd_set):
    if cmd_set == "esc_p_epson":
        return {
            "init": "\x1b\x40",
            "matrix_slower_prefix": "\x1b\x78\x01\x1b\x55\x01",
            "matrix_speed_restore": "\x1b\x78\x00\x1b\x55\x00",
            "double_strike_on": "\x1b\x47",
            "double_strike_off": "\x1b\x48",
            "bold_on": "\x1b\x45\x01",
            "bold_off": "\x1b\x46",
            "wide_on": "\x1b\x57\x01",
            "wide_off": "\x1b\x57\x00",
            "underline_on": "\x1b\x2d\x01",
            "underline_off": "\x1b\x2d\x00",
            "job_end": "\r\n\r\n",
        }
    return {
        "init": "\x1b\x40",
        "double_strike_on": "",
        "double_strike_off": "",
        "bold_on": "\x1b\x45\x01",
        "bold_off": "\x1b\x45\x00",
        "wide_on": "\x1d\x21\x20",
        "wide_off": "\x1d\x21\x00",
        "underline_on": "\x1b\x2d\x01",
        "underline_off": "\x1b\x2d\x00",
        "job_end": "\n\n",
    }


def _desc_width():
    return LINE_WIDTH - COL_IDX - COL_REF - COL_QTY - COL_COD - COL_BRAND - 5


def _join_row_parts(parts):
    return _GAP.join(parts)[:LINE_WIDTH]


def _cell(text, width):
    return (text or "")[:width].ljust(width)


def _format_table_row(first, ref, qty_str, cod, brand, desc):
    dw = _desc_width()
    parts = [
        _cell(first, COL_IDX),
        _cell(ref, COL_REF),
        _cell(qty_str, COL_QTY),
        _cell(cod, COL_COD),
        _cell(brand, COL_BRAND),
        _cell(desc, dw),
    ]
    return _join_row_parts(parts)


def _fill_line(left, right="", width=LINE_WIDTH):
    left = (left or "")[: width - 1]
    right = (right or "")[: width - 1]
    if len(left) + len(right) + 1 <= width:
        pad = width - len(left) - len(right)
        return left + (" " * max(pad, 1)) + right if right else left.ljust(width)[:width]
    return left[:width]


def _three_cols(a, b, c, width=LINE_WIDTH, gap=2):
    g = " " * gap
    inner = width - 2 * len(g)
    cw = inner // 3
    rest = inner - 3 * cw
    c0 = cw + (1 if rest > 0 else 0)
    c1 = cw + (1 if rest > 1 else 0)
    c2 = inner - c0 - c1
    sa = (a or "")[:c0].ljust(c0)
    sb = (b or "")[:c1].ljust(c1)
    sc = (c or "")[:c2].ljust(c2)
    return (sa + g + sb + g + sc)[:width]


def _product_brand(product, max_len=COL_BRAND):
    tmpl = product.product_tmpl_id
    brand = getattr(tmpl, "product_brand_id", False) or getattr(
        product, "product_brand_id", False
    )
    if brand:
        return (brand.name or "-")[:max_len]
    return "-"


def _product_ref(product):
    return (product.default_code or "-")[:COL_REF]


def _product_internal_code(product):
    tmpl = product.product_tmpl_id
    code = getattr(tmpl, "internal_code", None) or ""
    return (code or "-")[:COL_COD]


def _brand_sort_key(move):
    product = move.product_id
    tmpl = product.product_tmpl_id
    brand = getattr(tmpl, "product_brand_id", False) or getattr(
        product, "product_brand_id", False
    )
    bname = (brand.name or "").lower() if brand else "\uffff"
    return (bname, product.default_code or "", product.id, move.id)


def _invoice_ref(picking):
    if hasattr(picking, "sale_id") and picking.sale_id:
        invs = picking.sale_id.invoice_ids.filtered(
            lambda m: m.state == "posted" and m.move_type == "out_invoice"
        )
        if invs:
            invs = invs.sorted(key=lambda m: m.invoice_date or m.date, reverse=True)
            return invs[0].name or ""
    return picking.origin or ""


def _emission_date(picking):
    if picking.date_done:
        return fields.Date.to_date(picking.date_done)
    if picking.scheduled_date:
        return fields.Date.to_date(picking.scheduled_date)
    return fields.Date.context_today(picking)


class ReportStockPickingDispatchEscpos(models.AbstractModel):
    _name = "report.report_escpos_inventory.dispatch_escpos_doc"
    _description = "Nota de despacho ESC/POS"

    def _format_row(self, idx, move):
        product = move.product_id
        ref = _product_ref(product)
        icode = _product_internal_code(product)
        qty_val = move.quantity if move.quantity else move.product_uom_qty
        if qty_val == int(qty_val):
            qty_str = str(int(qty_val))
        else:
            qty_str = ("%.2f" % qty_val).rstrip("0").rstrip(".")
        qty_str = qty_str[:COL_QTY]
        marca = _product_brand(product, max_len=COL_BRAND)
        raw = product.name or ""
        desc = " ".join((raw or "").replace("\n", " ").split())
        line = _format_table_row(
            _cell(str(idx), COL_IDX),
            ref,
            qty_str,
            icode,
            marca,
            desc,
        )
        return [line]

    def _build_pages(self, picking):
        moves = picking.move_ids.filtered(
            lambda m: m.state != "cancel" and (m.product_uom_qty or m.quantity)
        ).sorted(key=_brand_sort_key)
        rows = []
        idx = 0
        for move in moves:
            idx += 1
            rows.append(self._format_row(idx, move))
        if not rows:
            rows = [[_fill_line("(Sin lineas de producto)", width=LINE_WIDTH)]]
        pages = []
        bucket = []
        used = 0
        nl = _nl("esc_p_epson")
        _, n_header = self._header_block(picking, 1, 1, nl)
        cap = _matrix_dispatch_max_product_lines(n_header)
        for row_lines in rows:
            need = len(row_lines)
            if bucket and used + need > cap:
                pages.append(bucket)
                bucket = []
                used = 0
            bucket.append(row_lines)
            used += need
        if bucket:
            pages.append(bucket)
        return pages

    def _padding_lines_before_footer(
        self, cmd_set, is_last, num_product_lines, header_line_count
    ):
        if cmd_set != "esc_p_epson":
            return 0
        foot = FOOTER_LINES_LAST if is_last else FOOTER_LINES_CONTINUE
        used = header_line_count + TABLE_HEADER_LINES + num_product_lines + foot
        page_lines = _matrix_letter_printable_lines()
        return max(0, page_lines - used)

    def _blank_fill_line(self):
        return " " * LINE_WIDTH

    def _header_block(self, picking, page_num, total_pages, nl):
        w = LINE_WIDTH
        company = picking.company_id
        partner = picking.partner_id
        comp_p = company.partner_id
        inv = _invoice_ref(picking) or "-"
        fecha = _emission_date(picking).strftime("%d/%m/%Y")
        l1 = (company.name or "-")[:w]
        l2 = ("Nota de despacho de la Factura: %s" % inv)[:w]
        rif_co = (comp_p.vat or company.vat or "-")[:16]
        l3 = ("RIF:%s  |  Fecha:%s  |  Pag:%s/%s" % (rif_co, fecha, page_num, total_pages))[:w]
        addr = ", ".join(
            p
            for p in [
                comp_p.street,
                comp_p.street2,
                comp_p.city,
                comp_p.state_id.name if comp_p.state_id else "",
            ]
            if p
        )[:w]
        l4 = addr or "-"
        cref = (partner.ref or str(partner.id) if partner else "-")[:10]
        cname = (partner.name or "-")[: w - 16]
        l5 = ("Cli:%s  %s" % (cref, cname))[:w]
        caddr = ""
        if partner:
            caddr = ", ".join(
                p
                for p in [
                    partner.street,
                    partner.street2,
                    partner.city,
                    partner.state_id.name if partner.state_id else "",
                ]
                if p
            )[:w]
        l6 = caddr or "-"
        pv = (partner.vat or "-")[:14]
        user = picking.user_id
        vend = (user.name if user else "-")[:14]
        if hasattr(picking, "sale_id") and picking.sale_id and picking.sale_id.user_id:
            vend = (picking.sale_id.user_id.name or vend)[:14]
        l7 = ("RIF:%s  Vend:%s  Alb:%s" % (pv, vend, (picking.name or "")[:16]))[:w]
        lines = [l1, l2, l3, l4, l5, l6, l7]
        return nl.join(lines) + nl, len(lines)

    def _table_header_block(self, nl, ctl, cmd_set):
        hdr = _format_table_row(
            "#",
            "Referencia",
            "Cant.",
            "Codigo",
            "Marca",
            "Desc.",
        )
        uon = ctl.get("underline_on") or ""
        uoff = ctl.get("underline_off") or ""
        if cmd_set != "esc_p_epson" and uon and uoff:
            hdr = uon + hdr + uoff
        return hdr + nl + ("-" * LINE_WIDTH) + nl

    def _footer_block(self, picking, page_num, total_pages, is_last, n_articulos, nl):
        w = LINE_WIDTH
        lines = []
        lines.append("-" * w)
        if not is_last:
            lines.append(_fill_line("--- CONTINUA ---", "P.%s/%s" % (page_num, total_pages)))
            return nl.join(lines) + nl
        bultos = len(picking.package_level_ids) if picking.package_level_ids else 0
        bultos_txt = str(bultos) if bultos else "____"
        lines.append(
            _fill_line("ARTICULOS:%s" % n_articulos, "BULTOS:%s" % bultos_txt, width=w)
        )
        lines.append(
            _three_cols(
                "Chq:____________",
                "Meson:__________",
                "Desp:___________",
                width=w,
                gap=3,
            )
        )
        lines.append(_fill_line("DESTINO:", "______________________________", width=w))
        lines.append("-" * w)
        return nl.join(lines) + nl

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        cmd_set = data.get("escpos_command_set") or "escpos"
        nl = _nl(cmd_set)
        ctl = _control_bytes(cmd_set)
        pickings = self.env["stock.picking"].browse(docids)
        out_parts = [ctl["init"]]
        if cmd_set == "esc_p_epson":
            out_parts.append(ctl.get("matrix_slower_prefix", ""))
            out_parts.append(ctl.get("double_strike_on", ""))
        for picking in pickings:
            pages = self._build_pages(picking)
            total_pages = len(pages)
            moves = picking.move_ids.filtered(
                lambda m: m.state != "cancel" and (m.product_uom_qty or m.quantity)
            )
            n_articulos = len(moves)
            for page_index, page_rows in enumerate(pages):
                page_num = page_index + 1
                is_last = page_num == total_pages
                header_block, n_header = self._header_block(
                    picking, page_num, total_pages, nl
                )
                out_parts.append(header_block)
                out_parts.append(self._table_header_block(nl, ctl, cmd_set))
                for row_lines in page_rows:
                    out_parts.append(nl.join(row_lines) + nl)
                n_prod = len(page_rows)
                pad = self._padding_lines_before_footer(
                    cmd_set, is_last, n_prod, n_header
                )
                for _ in range(pad):
                    out_parts.append(self._blank_fill_line() + nl)
                out_parts.append(
                    self._footer_block(
                        picking, page_num, total_pages, is_last, n_articulos, nl
                    )
                )
        tail = ""
        if cmd_set == "esc_p_epson":
            tail += ctl.get("double_strike_off", "")
        tail += ctl["bold_off"]
        if ctl.get("underline_off"):
            tail += ctl["underline_off"]
        tail += ctl.get("wide_off", "")
        if cmd_set == "esc_p_epson":
            tail += ctl.get("matrix_speed_restore", "")
            tail += "\x1b\x50\x1b\x32"
        else:
            tail += "\x1d\x21\x00"
        tail += ctl["job_end"]
        out_parts.append(tail)
        return {
            "doc_ids": docids,
            "doc_model": "stock.picking",
            "docs": pickings,
            "escpos_payload": Markup("".join(out_parts)),
        }
