# -*- coding: utf-8 -*-
import re

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.translate import _


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
    authorization_count = fields.Integer(compute="_compute_counts")
    gateway_count = fields.Integer(compute="_compute_counts")

    _sql_constraints = [
        (
            "device_bridge_code_uniq",
            "unique(code)",
            "The device code must be unique.",
        ),
    ]

    @api.depends("authorization_ids", "gateway_ids")
    def _compute_counts(self):
        for device in self:
            device.authorization_count = len(device.authorization_ids)
            device.gateway_count = len(device.gateway_ids)

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
        }

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
