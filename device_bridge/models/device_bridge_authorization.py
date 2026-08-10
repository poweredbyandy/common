# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools.translate import _


class DeviceBridgeAuthorization(models.Model):
    _name = "device.bridge.authorization"
    _description = "Device Bridge Authorization"
    _order = "write_date desc, id desc"

    name = fields.Char(required=True)
    device_id = fields.Many2one(
        "device.bridge",
        required=True,
        ondelete="cascade",
        index=True,
    )
    user_id = fields.Many2one(
        "res.users",
        required=True,
        default=lambda self: self.env.user,
        index=True,
        ondelete="cascade",
    )
    browser_key = fields.Char(required=True, index=True)
    connection_type = fields.Selection(
        selection=[
            ("webusb", "WebUSB"),
            ("serial", "Web Serial"),
            ("bluetooth", "Web Bluetooth"),
            ("other", "Other"),
        ],
        default="webusb",
        required=True,
    )
    vendor_id = fields.Integer(string="USB Vendor ID")
    product_id = fields.Integer(string="USB Product ID")
    serial_number = fields.Char()
    product_name = fields.Char()
    manufacturer_name = fields.Char()
    company_id = fields.Many2one(
        "res.company",
        related="device_id.company_id",
        store=True,
        index=True,
    )
    active = fields.Boolean(default=True)
    last_used = fields.Datetime()
    gateway_ids = fields.One2many(
        "device.bridge.gateway",
        "authorization_id",
        string="Gateways",
    )

    _sql_constraints = [
        (
            "device_bridge_auth_uniq",
            "unique(user_id, device_id, vendor_id, product_id, serial_number, browser_key)",
            "This device is already authorized for this user and browser.",
        ),
    ]

    @api.model
    def _normalize_browser_key(self, browser_key):
        key = (browser_key or "").strip()
        if not key:
            raise UserError(_("Missing browser key for device authorization."))
        return key[:128]

    def _ensure_own_record(self):
        if self.env.su:
            return
        if self.env.user.has_group("device_bridge.group_device_bridge_manager"):
            return
        if any(rec.user_id != self.env.user for rec in self):
            raise AccessError(_("You can only manage your own device authorizations."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault("user_id", self.env.uid)
            if not self.env.su and not self.env.user.has_group(
                "device_bridge.group_device_bridge_manager"
            ):
                vals["user_id"] = self.env.uid
        return super().create(vals_list)

    def write(self, vals):
        self._ensure_own_record()
        if (
            not self.env.su
            and not self.env.user.has_group(
                "device_bridge.group_device_bridge_manager"
            )
            and "user_id" in vals
            and vals["user_id"] != self.env.uid
        ):
            raise AccessError(_("You cannot reassign a device authorization."))
        return super().write(vals)

    def unlink(self):
        self._ensure_own_record()
        return super().unlink()

    @api.model
    def authorize_device(self, vals):
        vals = vals or {}
        device_code = vals.get("device_code") or vals.get("printer_code")
        browser_key = self._normalize_browser_key(vals.get("browser_key"))
        Device = self.env["device.bridge"]
        device = Device.search(
            [("code", "=", device_code), ("active", "=", True)], limit=1
        )
        if not device:
            raise UserError(_("Unknown device code: %s") % device_code)

        vendor_id = int(vals.get("vendor_id") or vals.get("vendorId") or 0)
        product_id = int(vals.get("product_id") or vals.get("productId") or 0)
        serial_number = (
            vals.get("serial_number") or vals.get("serialNumber") or ""
        ).strip()
        product_name = (
            vals.get("product_name") or vals.get("productName") or ""
        ).strip()
        manufacturer_name = (
            vals.get("manufacturer_name") or vals.get("manufacturerName") or ""
        ).strip()
        connection_type = (
            vals.get("connection_type") or vals.get("connectionType") or "webusb"
        ).strip().lower()
        if connection_type not in dict(self._fields["connection_type"].selection):
            connection_type = "webusb"

        domain = [
            ("device_id", "=", device.id),
            ("user_id", "=", self.env.uid),
            ("browser_key", "=", browser_key),
            ("vendor_id", "=", vendor_id),
            ("product_id", "=", product_id),
            ("serial_number", "=", serial_number),
        ]
        auth = self.with_context(active_test=False).search(domain, limit=1)
        values = {
            "name": product_name
            or manufacturer_name
            or "%s / %s" % (device.name, self.env.user.name),
            "device_id": device.id,
            "user_id": self.env.uid,
            "browser_key": browser_key,
            "connection_type": connection_type,
            "vendor_id": vendor_id,
            "product_id": product_id,
            "serial_number": serial_number,
            "product_name": product_name,
            "manufacturer_name": manufacturer_name,
            "active": True,
            "last_used": fields.Datetime.now(),
        }
        if auth:
            auth.write(values)
        else:
            auth = self.create(values)
        return auth._to_payload()

    @api.model
    def get_authorized_devices(self, device_code, browser_key):
        Device = self.env["device.bridge"]
        device = Device.search(
            [("code", "=", device_code), ("active", "=", True)], limit=1
        )
        if not device:
            return []
        browser_key = self._normalize_browser_key(browser_key)
        domain = [
            ("device_id", "=", device.id),
            ("user_id", "=", self.env.uid),
            ("active", "=", True),
        ]
        auths = self.search(domain + [("browser_key", "=", browser_key)])
        if not auths:
            # Same user, other browser profile / cleared localStorage key.
            auths = self.search(domain)
        return [auth._to_payload() for auth in auths]

    @api.model
    def touch_authorization(self, authorization_id, browser_key=None):
        auth = self.browse(int(authorization_id)).exists()
        if not auth:
            return False
        auth._ensure_own_record()
        values = {"last_used": fields.Datetime.now()}
        if browser_key:
            browser_key = self._normalize_browser_key(browser_key)
            if auth.browser_key != browser_key:
                values["browser_key"] = browser_key
        auth.write(values)
        return auth._to_payload()

    def _to_payload(self):
        self.ensure_one()
        return {
            "id": self.id,
            "name": self.name,
            "device_id": self.device_id.id,
            "device_code": self.device_id.code,
            "connection_type": self.connection_type,
            "vendor_id": self.vendor_id,
            "product_id": self.product_id,
            "serial_number": self.serial_number or "",
            "product_name": self.product_name or "",
            "manufacturer_name": self.manufacturer_name or "",
            "browser_key": self.browser_key,
            "last_used": fields.Datetime.to_string(self.last_used)
            if self.last_used
            else False,
        }
