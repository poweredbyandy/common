# -*- coding: utf-8 -*-
import base64
import re

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.translate import _

PRINTER_DEVICE_TYPES = ("printer", "label_printer")


class DeviceBridge(models.Model):
    _name = "device.bridge"
    _description = "Device Bridge"
    _order = "name, id"

    name = fields.Char(required=True, translate=True)
    code = fields.Char(
        required=True,
        index=True,
        help="Technical code used by JS proxies (e.g. pos80).",
    )
    device_type = fields.Selection(
        selection=[
            ("printer", "Printer"),
            ("label_printer", "Label printer"),
            ("scanner", "Barcode scanner"),
            ("scale", "Scale"),
            ("cash_drawer", "Cash drawer"),
            ("display", "Customer display"),
            ("other", "Other"),
        ],
        string="Device type",
        default="printer",
        required=True,
        index=True,
    )
    protocol = fields.Selection(
        selection=[
            ("escpos", "ESC/POS"),
            ("raw", "Raw"),
            ("epl", "EPL"),
            ("zpl", "ZPL"),
            ("hid", "HID"),
            ("none", "None"),
        ],
        default="escpos",
        required=True,
    )
    connection_types = fields.Char(
        string="Connection types",
        default="webusb,websocket",
        help="Comma-separated: webusb, websocket, serial, ...",
    )
    vendor_ids = fields.Char(
        string="USB Vendor IDs",
        help="Comma-separated USB vendor IDs in hex, e.g. 0483,0416,0fe6",
    )
    product_ids = fields.Char(
        string="USB Product IDs",
        help="Optional comma-separated USB product IDs in hex.",
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        default=lambda self: self.env.company,
        index=True,
    )
    authorization_ids = fields.One2many(
        "device.bridge.authorization",
        "device_id",
        string="Authorizations",
    )
    gateway_ids = fields.One2many(
        "device.bridge.gateway",
        "device_id",
        string="Gateways",
    )
    report_ids = fields.Many2many(
        "ir.actions.report",
        "device_bridge_ir_actions_report_rel",
        "device_id",
        "report_id",
        string="Reports",
        help="Reports that can be printed on this device.",
    )
    authorization_count = fields.Integer(compute="_compute_counts")
    gateway_count = fields.Integer(compute="_compute_counts")
    report_count = fields.Integer(compute="_compute_counts")

    _sql_constraints = [
        (
            "device_bridge_code_uniq",
            "unique(code)",
            "The device code must be unique.",
        ),
    ]

    @api.depends("authorization_ids", "gateway_ids", "report_ids")
    def _compute_counts(self):
        for device in self:
            device.authorization_count = len(device.authorization_ids)
            device.gateway_count = len(device.gateway_ids)
            device.report_count = len(device.report_ids)

    @api.constrains("device_type", "report_ids")
    def _check_report_ids_device_type(self):
        for device in self:
            if device.report_ids and device.device_type not in PRINTER_DEVICE_TYPES:
                raise ValidationError(
                    _("Reports can only be assigned to a printer.")
                )

    @api.onchange("device_type")
    def _onchange_device_type(self):
        if self.device_type not in PRINTER_DEVICE_TYPES:
            self.report_ids = False

    @api.model
    def _normalize_code(self, code, name=None):
        raw = (code or name or "").strip().lower()
        raw = re.sub(r"[^a-z0-9_]+", "_", raw)
        raw = re.sub(r"_+", "_", raw).strip("_")
        if not raw:
            raise UserError(_("A technical code is required."))
        return raw[:64]

    @api.model
    def _append_hex_id(self, current, value):
        token = "%04x" % int(value)
        parts = [
            part.strip().lower().replace("0x", "")
            for part in (current or "").replace(";", ",").split(",")
            if part.strip()
        ]
        if token not in parts:
            parts.append(token)
        return ",".join(parts)

    def _parse_hex_id_list(self, value):
        self.ensure_one()
        result = []
        for part in (value or "").replace(";", ",").split(","):
            token = part.strip().lower().replace("0x", "")
            if not token:
                continue
            try:
                result.append(int(token, 16))
            except ValueError:
                continue
        return result

    def get_usb_filters(self, picker=False):
        self.ensure_one()
        vendors = self._parse_hex_id_list(self.vendor_ids)
        products = self._parse_hex_id_list(self.product_ids)
        if not vendors:
            return [{}]
        filters = []
        for vendor_id in vendors:
            # Picker: vendor-only so Chrome lists the device even if product_id drifted.
            if picker or not products:
                filters.append({"vendorId": vendor_id})
            else:
                for product_id in products:
                    filters.append(
                        {"vendorId": vendor_id, "productId": product_id}
                    )
        return filters

    def _connection_type_list(self):
        self.ensure_one()
        return [
            part.strip().lower()
            for part in (self.connection_types or "").split(",")
            if part.strip()
        ]

    def _sanitize_print_field(self, value):
        text = (value or "").replace("\x00", " ").strip()
        return re.sub(r"[\r\n^~\"\\]", " ", text)[:40]

    def _get_test_print_bytes(self):
        self.ensure_one()
        if self.protocol == "none":
            return b""
        name = self._sanitize_print_field(self.name) or "Device Bridge"
        code = self._sanitize_print_field(self.code) or "printer"
        if self.protocol == "zpl":
            label = (
                "^XA\r\n"
                "^PW812\r\n"
                "^LL406\r\n"
                "^LH0,0\r\n"
                "^CI28\r\n"
                "^FO20,20^GB360,160,4^FS\r\n"
                "^FO40,40^A0N,40,40^FDDevice Bridge^FS\r\n"
                "^FO40,100^A0N,28,28^FD%s^FS\r\n"
                "^FO40,150^A0N,24,24^FD%s / ZPL^FS\r\n"
                "^XZ\r\n"
            ) % (name, code)
            return label.encode("ascii", "replace")
        if self.protocol == "epl":
            label = (
                "\nN\n"
                'A40,40,0,3,1,1,N,"Device Bridge"\n'
                'A40,80,0,3,1,1,N,"%s"\n'
                'A40,120,0,3,1,1,N,"%s / EPL"\n'
                "P1\n"
            ) % (name, code)
            return label.encode("ascii", "replace")
        payload = bytearray(b"\x1b\x40\x1b\x61\x01")
        payload.extend(b"Device Bridge\n")
        payload.extend(name.encode("utf-8", "replace"))
        payload.extend(b"\n")
        payload.extend(code.encode("ascii", "replace"))
        payload.extend(b" / ESC POS\n\n\n\x1d\x56\x00")
        return bytes(payload)

    @api.model
    def get_test_print_payload(self, code):
        device = self.search([("code", "=", code), ("active", "=", True)], limit=1)
        if not device:
            raise UserError(_("Unknown device code: %s") % code)
        if device.device_type not in PRINTER_DEVICE_TYPES:
            raise UserError(_("Test print is only available for printers."))
        raw = device._get_test_print_bytes()
        if not raw:
            raise UserError(_("This device has no print protocol."))
        return {
            "code": device.code,
            "name": device.name,
            "protocol": device.protocol,
            "data_b64": base64.b64encode(raw).decode(),
        }

    def action_print_test(self):
        self.ensure_one()
        self.get_test_print_payload(self.code)
        return {
            "type": "ir.actions.client",
            "tag": "device_bridge_print_test",
            "params": {
                "device_code": self.code,
            },
            "context": {
                "device_code": self.code,
            },
        }

    @api.model
    def get_device_payload(self, code):
        device = self.search([("code", "=", code), ("active", "=", True)], limit=1)
        if not device:
            return {}
        return {
            "id": device.id,
            "name": device.name,
            "code": device.code,
            "device_type": device.device_type,
            "protocol": device.protocol,
            "connection_types": device._connection_type_list(),
            "filters": device.get_usb_filters(),
            "report_ids": device.report_ids.ids,
            "report_names": device.report_ids.mapped("report_name"),
        }

    @api.model
    def get_printers_for_report(self, report_ref):
        report = self.env["ir.actions.report"]._get_report(report_ref)
        printers = report.device_bridge_ids.filtered(
            lambda device: device.active
            and device.device_type in PRINTER_DEVICE_TYPES
        )
        return [self.get_device_payload(printer.code) for printer in printers]

    @api.model
    def get_register_defaults(self):
        def _selection_labels(field_name):
            selection = self._fields[field_name].selection
            if callable(selection):
                selection = selection(self)
            return [
                (value, self.env._(label) if isinstance(label, str) else label)
                for value, label in selection
            ]

        return {
            "device_types": _selection_labels("device_type"),
            "protocols": _selection_labels("protocol"),
            "defaults": {
                "device_type": "printer",
                "protocol": "escpos",
                "share_websocket": True,
                "connection_type": "webusb",
            },
        }

    @api.model
    def register_browser_device(self, vals):
        vals = vals or {}
        Auth = self.env["device.bridge.authorization"]
        name = Auth._sanitize_text(vals.get("name") or "")
        if not name:
            raise UserError(_("Device name is required."))
        code = self._normalize_code(vals.get("code"), name)
        device_type = vals.get("device_type") or "printer"
        if device_type not in dict(self._fields["device_type"].selection):
            raise UserError(_("Invalid device type."))
        protocol = vals.get("protocol") or "escpos"
        if protocol not in dict(self._fields["protocol"].selection):
            raise UserError(_("Invalid protocol."))

        vendor_id = int(vals.get("vendor_id") or 0)
        product_id = int(vals.get("product_id") or 0)
        if not vendor_id:
            raise UserError(_("Select a USB device before saving."))

        share_websocket = bool(vals.get("share_websocket", True))
        connection_types = "webusb,websocket" if share_websocket else "webusb"

        device = self.with_context(active_test=False).search(
            [("code", "=", code)], limit=1
        )
        device_vals = {
            "name": name,
            "code": code,
            "device_type": device_type,
            "protocol": protocol,
            "connection_types": connection_types,
            "vendor_ids": self._append_hex_id(
                device.vendor_ids if device else "", vendor_id
            ),
            "product_ids": self._append_hex_id(
                device.product_ids if device else "", product_id
            )
            if product_id
            else (device.product_ids if device else False),
            "active": True,
            "company_id": self.env.company.id,
        }
        if device:
            device.write(device_vals)
        else:
            device = self.create(device_vals)

        auth = self.env["device.bridge.authorization"].authorize_device(
            {
                "device_code": device.code,
                "browser_key": vals.get("browser_key"),
                "connection_type": vals.get("connection_type") or "webusb",
                "vendor_id": vendor_id,
                "product_id": product_id,
                "serial_number": vals.get("serial_number") or "",
                "product_name": vals.get("product_name") or "",
                "manufacturer_name": vals.get("manufacturer_name") or "",
            }
        )
        return {
            "device_id": device.id,
            "authorization_id": auth.get("id"),
            "code": device.code,
            "name": device.name,
        }
