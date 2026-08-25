# -*- coding: utf-8 -*-
import base64

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _

from .device_bridge import PRINTER_DEVICE_TYPES


def _to_print_bytes(content):
    if content is None:
        return b""
    if isinstance(content, bytes):
        return content
    if isinstance(content, memoryview):
        return content.tobytes()
    if hasattr(content, "getvalue"):
        return content.getvalue()
    return str(content).encode("utf-8")


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    device_bridge_ids = fields.Many2many(
        "device.bridge",
        "device_bridge_ir_actions_report_rel",
        "report_id",
        "device_id",
        string="Device Bridge printers",
        domain=[
            ("device_type", "in", PRINTER_DEVICE_TYPES),
            ("active", "=", True),
        ],
        help="Printers that can print this report through Device Bridge.",
    )

    def _get_readable_fields(self):
        return super()._get_readable_fields() | {
            "device_bridge_ids",
        }

    def _device_bridge_printers(self):
        self.ensure_one()
        return self.device_bridge_ids.filtered(
            lambda device: device.active
            and device.device_type in PRINTER_DEVICE_TYPES
        )

    @api.model
    def prepare_device_bridge_print(self, report_ref, res_ids=None, data=None):
        report = self._get_report(report_ref)
        printers = report._device_bridge_printers()
        if not printers:
            return False
        if res_ids is None:
            res_ids = []
        elif isinstance(res_ids, int):
            res_ids = [res_ids]
        rendered = self._render(report, res_ids, data=data or {})
        if not rendered:
            return False
        content, _extension = rendered
        raw = _to_print_bytes(content)
        if not raw:
            raise UserError(_("The report produced no data to print."))
        Device = self.env["device.bridge"]
        return {
            "printers": [Device.get_device_payload(printer.code) for printer in printers],
            "data_b64": base64.b64encode(raw).decode(),
            "report_type": report.report_type,
            "name": report.name,
        }
