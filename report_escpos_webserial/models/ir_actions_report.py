# -*- coding: utf-8 -*-

import logging

from markupsafe import Markup

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


def _escpos_add_column_if_missing(cr, column, ddl):
    cr.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'ir_act_report_xml' AND column_name = %s
        """,
        (column,),
    )
    if not cr.fetchone():
        cr.execute(ddl)


def _escpos_ensure_ir_act_report_columns(cr):
    _escpos_add_column_if_missing(
        cr,
        "escpos_command_set",
        "ALTER TABLE ir_act_report_xml ADD COLUMN escpos_command_set VARCHAR DEFAULT 'escpos'",
    )
    _escpos_add_column_if_missing(
        cr,
        "escpos_log_payload",
        "ALTER TABLE ir_act_report_xml ADD COLUMN escpos_log_payload BOOLEAN DEFAULT FALSE",
    )
    _escpos_add_column_if_missing(
        cr,
        "escpos_transport",
        "ALTER TABLE ir_act_report_xml ADD COLUMN escpos_transport VARCHAR DEFAULT 'webserial'",
    )
    _escpos_add_column_if_missing(
        cr,
        "escpos_usb_vendor_id",
        "ALTER TABLE ir_act_report_xml ADD COLUMN escpos_usb_vendor_id INTEGER",
    )
    _escpos_add_column_if_missing(
        cr,
        "escpos_usb_product_id",
        "ALTER TABLE ir_act_report_xml ADD COLUMN escpos_usb_product_id INTEGER",
    )


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    report_type = fields.Selection(
        selection_add=[("qweb-escpos", "ESC/POS (WebSerial)")],
        ondelete={"qweb-escpos": "set qweb-pdf"},
    )
    escpos_profile = fields.Selection(
        [
            ("generic", "Genérico 58/80 mm"),
            ("epson_tm", "Epson TM"),
            ("star", "Star"),
            ("citizen", "Citizen"),
            ("bixolon", "Bixolon"),
        ],
        string="Perfil ESC/POS",
        default="generic",
        help="Perfil del hardware: el informe QWeb puede usarlo para márgenes o comandos.",
    )
    escpos_transport = fields.Selection(
        [
            ("webserial", "WebSerial (puerto COM)"),
            ("webusb", "WebUSB (USB directo)"),
        ],
        string="Canal ESC/POS",
        default="webserial",
        help="WebUSB envía bytes al endpoint bulk. Si Windows/macOS tiene driver de impresión "
        "activo, el navegador puede mostrar «Access denied» al abrir el USB: use WebSerial (COM) "
        "o libere el dispositivo (desinstalar impresora / WinUSB avanzado).",
    )
    escpos_usb_vendor_id = fields.Integer(
        string="USB Vendor ID",
        help="Identificador hexadecimal del fabricante (p. ej. 1208 para Epson). "
        "Dejar vacío para listar todos los USB (puede ser largo).",
    )
    escpos_usb_product_id = fields.Integer(
        string="USB Product ID",
        help="Opcional. Si se rellena, filtra junto al Vendor ID.",
    )
    escpos_baud_rate = fields.Integer(
        string="Velocidad serie (baudios)",
        default=9600,
        help="Velocidad por defecto al abrir el puerto serie en el navegador.",
    )
    escpos_encoding = fields.Selection(
        [
            ("cp437", "CP437"),
            ("latin-1", "Latin-1 (ISO-8859-1)"),
            ("utf-8", "UTF-8"),
        ],
        string="Codificación de bytes",
        default="cp437",
        required=True,
    )
    escpos_log_payload = fields.Boolean(
        string="Registrar salida en el log",
        default=False,
        help="Si está activo, cada impresión escribe el contenido del informe en el log del "
        "servidor (consola / odoo.log) con los bytes de control escapados. No se envía nada a "
        "la impresora ni se abre el selector de puerto USB/COM.",
    )
    escpos_command_set = fields.Selection(
        [
            ("escpos", "ESC/POS (térmico / recibo)"),
            ("esc_p_epson", "ESC/P Epson matriz (LX/LQ, etc.)"),
        ],
        string="Juego de comandos",
        default="escpos",
        required=True,
        help="ESC/POS usa secuencias típicas de tickets (p. ej. negrita ESC E 0/1). "
        "ESC/P Epson matriz usa fin de negrita con ESC F, subrayado en cabecera de tabla "
        "(ESC - 1/0), sin form feed al cierre (evita error de corte en LX sin cortador), y "
        "relleno de líneas hasta altura de página fija.",
    )

    def _get_readable_fields(self):
        return super()._get_readable_fields() | {
            "escpos_profile",
            "escpos_transport",
            "escpos_usb_vendor_id",
            "escpos_usb_product_id",
            "escpos_baud_rate",
            "escpos_encoding",
            "escpos_log_payload",
            "escpos_command_set",
        }

    @api.model
    def _render_qweb_escpos(self, report_ref, docids, data=None):
        if not data:
            data = {}
        data.setdefault("report_type", "escpos")
        report = self._get_report(report_ref)
        merged = dict(data or {})
        if report.report_type == "qweb-escpos":
            merged["escpos_command_set"] = report.escpos_command_set or "escpos"
        data = self._get_rendering_context(report, docids, merged)
        data["escpos_profile"] = report.escpos_profile
        data["escpos_encoding"] = report.escpos_encoding
        if "escpos_payload" in data:
            text = str(data["escpos_payload"])
        else:
            rendered = self._render_template(report.report_name, data)
            if isinstance(rendered, Markup):
                text = str(rendered)
            else:
                text = rendered
        if report.escpos_log_payload:
            preview = "".join(
                ch
                if ch in "\n\r\t" or (len(ch) == 1 and ch.isprintable())
                else "\\x%02x" % ord(ch)
                for ch in text
            )
            _logger.info(
                "ESC/POS report=%s model=%s docids=%s\n%s",
                report.report_name,
                report.model,
                docids,
                preview,
            )
        encoding = report.escpos_encoding or "cp437"
        return text.encode(encoding, errors="replace"), "escpos"

    def report_action(self, docids, data=None, config=True):
        res = super().report_action(docids, data=data, config=config)
        if (
            isinstance(res, dict)
            and res.get("type") == "ir.actions.report"
            and self.report_type == "qweb-escpos"
        ):
            res["escpos_profile"] = self.escpos_profile
            res["escpos_baud_rate"] = self.escpos_baud_rate
            res["escpos_encoding"] = self.escpos_encoding
            res["escpos_transport"] = self.escpos_transport
            res["escpos_usb_vendor_id"] = self.escpos_usb_vendor_id or 0
            res["escpos_usb_product_id"] = self.escpos_usb_product_id or 0
            res["escpos_log_payload"] = bool(self.escpos_log_payload)
            res["escpos_command_set"] = self.escpos_command_set or "escpos"
        return res

    @api.private
    def init(self):
        super().init()
        _escpos_ensure_ir_act_report_columns(self.env.cr)
