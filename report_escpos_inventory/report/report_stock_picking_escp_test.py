# -*- coding: utf-8 -*-

from markupsafe import Markup

from odoo import api, models

from .report_stock_picking_dispatch_escpos import _control_bytes, _nl

W = 80
MAX_LINES = 60


def _pad(s):
    s = s or ""
    return (s.replace("\n", " "))[:W]


class ReportStockPickingEscpTest(models.AbstractModel):
    _name = "report.report_escpos_inventory.escp_demo_doc"
    _description = "Prueba formatos ESC/P en albaran"

    def _push(self, lines, s):
        if len(lines) >= MAX_LINES:
            return
        lines.append(_pad(s))

    def _lines_esc_p_epson(self, lines):
        self._push(lines, "DEMO ESC/P EPSON (LX/LQ) - max %s lineas" % MAX_LINES)
        self._push(lines, "")
        self._push(lines, "--- Pica 10 CPI (ESC P) ---")
        self._push(lines, "\x1b\x50" + "ABCDEFGH" * 10)
        self._push(lines, "")
        self._push(lines, "--- Elite 12 CPI (ESC M) ---")
        self._push(lines, "\x1b\x4d" + "abcdefghijkl" * 6 + "abcd")
        self._push(lines, "")
        self._push(lines, "--- Tipos de letra ESC k (Roman/Sans/Courier) ---")
        self._push(lines, "\x1b\x6b\x00" + "Fuente Roman k=0 (predeterminada muchas LX)")
        self._push(lines, "\x1b\x6b\x01" + "Fuente Sans k=1 (si la impresora la trae)")
        self._push(lines, "\x1b\x6b\x02" + "Fuente Courier k=2 monoespaciada")
        self._push(lines, "\x1b\x6b\x00" + "Vuelta a Roman k=0")
        self._push(lines, "")
        self._push(lines, "--- Calidad borrador / LQ (ESC x) ---")
        self._push(lines, "\x1b\x78\x01" + "ESC x1: mas definido si el modelo soporta LQ")
        self._push(lines, "\x1b\x78\x00" + "ESC x0: modo borrador / rapido si aplica")
        self._push(lines, "")
        self._push(lines, "--- Tabla codigos ESC t (pagina de caracteres) ---")
        self._push(lines, "\x1b\x74\x00" + "PC437 (t=0) " + "\x1b\x74\x13" + " CP858 euro (t=19)")
        self._push(lines, "\x1b\x74\x00" + "Vuelta PC437")
        self._push(lines, "")
        self._push(lines, "--- Juego internacional ESC R ---")
        self._push(lines, "\x1b\x52\x00" + "USA R=0")
        self._push(lines, "\x1b\x52\x06" + "Espana II R=6 (si firmware lo admite)")
        self._push(lines, "\x1b\x52\x00" + "Vuelta USA")
        self._push(lines, "")
        self._push(lines, "--- Condensado SI / DC2 ---")
        self._push(lines, "\x0f" + "Texto condensado misma linea fisica.")
        self._push(lines, "\x12" + "Cancel condensado.")
        self._push(lines, "")
        self._push(lines, "--- Negrita ESC E / ESC F ---")
        self._push(lines, "\x1b\x45\x01" + "ENFASIS" + "\x1b\x46" + "  normal")
        self._push(lines, "")
        self._push(lines, "--- Doble impacto ESC G / ESC H ---")
        self._push(lines, "\x1b\x47" + "Doble golpe" + "\x1b\x48")
        self._push(lines, "")
        self._push(lines, "--- Subrayado / cursiva ---")
        self._push(
            lines,
            "\x1b\x2d\x01" + "subrayado" + "\x1b\x2d\x00" + "  " + "\x1b\x34" + "cursiva" + "\x1b\x35" + " normal",
        )
        self._push(lines, "")
        self._push(lines, "--- Ancho doble ESC W ---")
        self._push(lines, "\x1b\x57\x01" + "ANCHO" + "\x1b\x57\x00\x1b\x50 pica")
        self._push(lines, "")
        self._push(lines, "--- Interlineado 1/6 y 1/8 ---")
        self._push(lines, "\x1b\x32" + "1/6 pulg  " + "\x1b\x30" + "1/8 pulg" + "\x1b\x32" + " otra vez 1/6")
        self._push(lines, "")
        self._push(lines, "Latin-1: nino nina; simbolos 0-9 #%=+-|")
        self._push(lines, "Ref x3.5 " + "\x1b\x45\x01" + "Ref x3.5 negrita" + "\x1b\x46")
        self._push(lines, "-" * 40 + "=" * 40 + " Sin FF. FIN")
        return lines[:MAX_LINES]

    def _lines_escpos(self, lines):
        self._push(lines, "DEMO ESC/POS (ticket) - subconjunto")
        self._push(lines, "")
        self._push(lines, "--- Tamano caracter GS ! ---")
        self._push(lines, "\x1d\x21\x00" + "Normal GS!0")
        self._push(lines, "\x1d\x21\x11" + "DOBLE" + "\x1d\x21\x00" + " normal")
        self._push(lines, "\x1d\x21\x10" + "Doble alto" + "\x1d\x21\x00")
        self._push(lines, "\x1d\x21\x20" + "Doble ancho" + "\x1d\x21\x00")
        self._push(lines, "")
        self._push(lines, "--- Tabla codigos ESC t (TM) ---")
        self._push(lines, "\x1b\x74\x00" + "t=0 PC437  " + "\x1b\x74\x10" + " t=16 WPC1252")
        self._push(lines, "\x1b\x74\x00" + "Vuelta PC437")
        self._push(lines, "")
        self._push(lines, "--- Negrita / subrayado ---")
        self._push(lines, "\x1b\x45\x01" + "Negrita" + "\x1b\x45\x00" + "  \x1b\x2d\x01sub\x1b\x2d\x00")
        self._push(lines, "")
        self._push(lines, "Latin-1 prueba. Ver modo matriz para fuentes ESC k.")
        self._push(lines, "FIN DEMO termico.")
        return lines[:MAX_LINES]

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data or {}
        cmd_set = data.get("escpos_command_set") or "esc_p_epson"
        nl = _nl(cmd_set)
        ctl = _control_bytes(cmd_set)
        lines = []
        if cmd_set == "esc_p_epson":
            lines = self._lines_esc_p_epson(lines)
        else:
            lines = self._lines_escpos(lines)
        lines = lines[:MAX_LINES]
        body = nl.join(lines) + nl
        tail = ctl["bold_off"]
        if ctl.get("underline_off"):
            tail += ctl["underline_off"]
        if cmd_set == "esc_p_epson":
            tail += "\x1b\x50\x1b\x32"
        else:
            tail += "\x1d\x21\x00"
        tail += nl + nl
        payload = ctl["init"] + body + tail
        return {
            "doc_ids": docids,
            "doc_model": "stock.picking",
            "docs": self.env["stock.picking"].browse(docids),
            "escpos_payload": Markup(payload),
        }
