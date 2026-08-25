# -*- coding: utf-8 -*-
import base64
import logging
import uuid
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

ONLINE_SECONDS = 180
BUS_NOTIFICATION = "device_bridge/print_job"


class DeviceBridgeGateway(models.Model):
    _name = "device.bridge.gateway"
    _description = "Device Bridge Gateway"
    _order = "last_seen desc, id desc"

    name = fields.Char(required=True)
    device_id = fields.Many2one(
        "device.bridge",
        required=True,
        ondelete="cascade",
        index=True,
    )
    authorization_id = fields.Many2one(
        "device.bridge.authorization",
        required=True,
        ondelete="cascade",
        index=True,
    )
    user_id = fields.Many2one(
        "res.users",
        required=True,
        index=True,
        ondelete="cascade",
    )
    browser_key = fields.Char(required=True, index=True)
    channel_token = fields.Char(required=True, index=True, copy=False)
    last_seen = fields.Datetime(required=True, index=True)
    device_label = fields.Char()
    company_id = fields.Many2one(
        "res.company",
        related="device_id.company_id",
        store=True,
        index=True,
    )
    is_online = fields.Boolean(compute="_compute_is_online", store=False)

    @api.depends("last_seen")
    def _compute_is_online(self):
        now = fields.Datetime.now()
        for gateway in self:
            if not gateway.last_seen:
                gateway.is_online = False
                continue
            gateway.is_online = gateway.last_seen >= now - timedelta(
                seconds=ONLINE_SECONDS
            )

    def _is_online(self):
        self.ensure_one()
        if not self.last_seen:
            return False
        return self.last_seen >= fields.Datetime.now() - timedelta(
            seconds=ONLINE_SECONDS
        )

    @api.model
    def _online_domain(self):
        return [
            (
                "last_seen",
                ">=",
                fields.Datetime.now() - timedelta(seconds=ONLINE_SECONDS),
            )
        ]

    @api.model
    def register_gateway(self, device_code, browser_key, authorization_id, label=None):
        Auth = self.env["device.bridge.authorization"]
        Device = self.env["device.bridge"]
        browser_key = Auth._normalize_browser_key(browser_key)
        device = Device.search(
            [("code", "=", device_code), ("active", "=", True)], limit=1
        )
        if not device:
            raise UserError(_("Unknown device code: %s") % device_code)

        auth = Auth.sudo().browse(int(authorization_id or 0)).exists()
        if (
            not auth
            or auth.user_id.id != self.env.user.id
            or not auth.active
            or auth.device_id != device
        ):
            auth = Auth.sudo().search(
                [
                    ("device_id", "=", device.id),
                    ("user_id", "=", self.env.user.id),
                    ("active", "=", True),
                ],
                order="last_used desc, id desc",
                limit=1,
            )
        if not auth:
            raise AccessError(_("Invalid device authorization for gateway."))

        if "websocket" not in device._connection_type_list():
            raise UserError(
                _("Device %s does not allow WebSocket sharing.") % device.name
            )

        if auth.browser_key != browser_key:
            auth.write({"browser_key": browser_key})

        label = Auth._sanitize_text(label)
        gateway = self.sudo().search(
            [
                ("device_id", "=", device.id),
                ("user_id", "=", self.env.user.id),
                ("browser_key", "=", browser_key),
            ],
            limit=1,
        )
        values = {
            "name": label
            or auth.name
            or "%s gateway" % auth.device_id.name,
            "device_id": auth.device_id.id,
            "authorization_id": auth.id,
            "user_id": self.env.user.id,
            "browser_key": browser_key,
            "device_label": label or auth.product_name or auth.name,
            "last_seen": fields.Datetime.now(),
            "channel_token": gateway.channel_token if gateway else uuid.uuid4().hex,
        }
        if gateway:
            gateway.write(values)
        else:
            gateway = self.sudo().create(values)
        return gateway._to_payload()

    @api.model
    def heartbeat(self, gateway_id, browser_key, channel_token):
        Auth = self.env["device.bridge.authorization"]
        browser_key = Auth._normalize_browser_key(browser_key)
        gateway = self.sudo().browse(int(gateway_id)).exists()
        if (
            not gateway
            or gateway.user_id.id != self.env.user.id
            or gateway.browser_key != browser_key
            or gateway.channel_token != (channel_token or "")
        ):
            raise AccessError(_("Invalid gateway heartbeat."))
        gateway.write({"last_seen": fields.Datetime.now()})
        return gateway._to_payload()

    @api.model
    def unregister_gateway(self, gateway_id, browser_key, channel_token):
        Auth = self.env["device.bridge.authorization"]
        browser_key = Auth._normalize_browser_key(browser_key)
        gateway = self.sudo().browse(int(gateway_id)).exists()
        if (
            not gateway
            or gateway.user_id.id != self.env.user.id
            or gateway.browser_key != browser_key
            or gateway.channel_token != (channel_token or "")
        ):
            raise AccessError(_("Invalid gateway unregister."))
        gateway.unlink()
        return True

    @api.model
    def get_online_gateways(self, device_code):
        Device = self.env["device.bridge"]
        device = Device.search(
            [("code", "=", device_code), ("active", "=", True)], limit=1
        )
        if not device:
            return []
        if "websocket" not in device._connection_type_list():
            return []
        gateways = self.sudo().search(
            [("device_id", "=", device.id)] + self._online_domain(),
            order="last_seen desc",
        )
        # Share within same company by default
        allowed_companies = self.env.companies
        gateways = gateways.filtered(
            lambda g: not g.company_id or g.company_id in allowed_companies
        )
        return [g._to_public_payload() for g in gateways]

    @api.model
    def send_raw_job(self, device_code, data_b64, gateway_id=None):
        if not data_b64:
            raise UserError(_("Empty print payload."))
        try:
            raw = base64.b64decode(data_b64, validate=True)
        except Exception as err:
            raise UserError(_("Invalid base64 payload.")) from err
        if not raw:
            raise UserError(_("Empty print payload."))

        Device = self.env["device.bridge"]
        device = Device.search(
            [("code", "=", device_code), ("active", "=", True)], limit=1
        )
        if not device:
            raise UserError(_("Unknown device code: %s") % device_code)
        if "websocket" not in device._connection_type_list():
            raise UserError(
                _("Device %s does not allow remote WebSocket jobs.") % device.name
            )

        domain = [("device_id", "=", device.id)] + self._online_domain()
        if gateway_id:
            domain.append(("id", "=", int(gateway_id)))
        gateway = self.sudo().search(domain, order="last_seen desc", limit=1)
        if not gateway:
            raise UserError(
                _(
                    "No online gateway found for device %s. "
                    "Keep a browser connected to the physical device."
                )
                % device.name
            )
        if gateway.company_id and gateway.company_id not in self.env.companies:
            raise AccessError(_("Gateway belongs to another company."))

        Job = self.env["device.bridge.print.job"]
        if not Job._ensure_table():
            raise UserError(_("Print job storage is not available."))
        job_id = uuid.uuid4().hex
        job = Job.sudo().create(
            {
                "name": job_id,
                "device_id": device.id,
                "gateway_id": gateway.id,
                "requester_id": self.env.uid,
                "data_b64": data_b64,
                "state": "pending",
            }
        )
        payload = {
            "job_id": job.name,
            "record_id": job.id,
            "gateway_id": gateway.id,
            "authorization_id": gateway.authorization_id.id,
            "browser_key": gateway.browser_key,
            "channel_token": gateway.channel_token,
            "device_code": device.code,
            "data_b64": data_b64,
            "requester_uid": self.env.user.id,
            "requester_name": self.env.user.name,
        }
        gateway.user_id._bus_send(BUS_NOTIFICATION, payload)
        _logger.info(
            "device_bridge job %s queued on gateway %s for device %s by uid=%s",
            job_id,
            gateway.id,
            device.code,
            self.env.uid,
        )
        return {
            "job_id": job_id,
            "gateway_id": gateway.id,
            "gateway_name": gateway.name,
            "device_code": device.code,
        }

    def _ensure_caller_gateway(self, gateway_id, browser_key, channel_token):
        Auth = self.env["device.bridge.authorization"]
        browser_key = Auth._normalize_browser_key(browser_key)
        gateway = self.sudo().browse(int(gateway_id)).exists()
        if (
            not gateway
            or gateway.user_id.id != self.env.user.id
            or gateway.browser_key != browser_key
            or gateway.channel_token != (channel_token or "")
        ):
            raise AccessError(_("Invalid gateway."))
        return gateway

    def _claim_pending_jobs(self):
        self.ensure_one()
        Job = self.env["device.bridge.print.job"]
        if not Job._ensure_table():
            return []
        jobs = Job.sudo().search(
            [
                ("gateway_id", "=", self.id),
                ("state", "=", "pending"),
            ],
            order="id",
        )
        if jobs:
            jobs.write({"state": "processing"})
        return [job._to_payload() for job in jobs]

    @api.model
    def claim_print_job(self, job_id, gateway_id, browser_key, channel_token):
        gateway = self._ensure_caller_gateway(
            gateway_id, browser_key, channel_token
        )
        Job = self.env["device.bridge.print.job"]
        if not Job._ensure_table():
            return False
        job = Job.sudo().browse(int(job_id)).exists()
        if not job or job.gateway_id != gateway:
            return False
        if job.state == "pending":
            job.write({"state": "processing"})
            return True
        return False

    @api.model
    def get_my_gateways(self, browser_key):
        Auth = self.env["device.bridge.authorization"]
        browser_key = Auth._normalize_browser_key(browser_key)
        gateways = self.sudo().search(
            [
                ("user_id", "=", self.env.uid),
                ("browser_key", "=", browser_key),
            ]
            + self._online_domain(),
            order="last_seen desc",
        )
        return [gateway._to_payload() for gateway in gateways]

    @api.model
    def pull_print_jobs(self, gateway_id, browser_key, channel_token):
        gateway = self._ensure_caller_gateway(
            gateway_id, browser_key, channel_token
        )
        gateway.write({"last_seen": fields.Datetime.now()})
        try:
            return gateway._claim_pending_jobs()
        except Exception:
            _logger.exception("device_bridge pull_print_jobs failed")
            return []

    @api.model
    def ack_print_job(
        self, job_id, gateway_id, browser_key, channel_token, success=True, error=None
    ):
        gateway = self._ensure_caller_gateway(
            gateway_id, browser_key, channel_token
        )
        Job = self.env["device.bridge.print.job"]
        if not Job._ensure_table():
            return False
        job = Job.sudo().browse(int(job_id)).exists()
        if not job or job.gateway_id != gateway:
            return False
        if success:
            job.write({"state": "done", "error_message": False})
        else:
            job.write(
                {
                    "state": "error",
                    "error_message": (error or "")[:256],
                }
            )
        return True

    def _to_payload(self):
        self.ensure_one()
        return {
            "id": self.id,
            "name": self.name,
            "device_code": self.device_id.code,
            "authorization_id": self.authorization_id.id,
            "browser_key": self.browser_key,
            "channel_token": self.channel_token,
            "device_label": self.device_label or "",
            "last_seen": fields.Datetime.to_string(self.last_seen),
            "is_online": self._is_online(),
        }

    def _to_public_payload(self):
        self.ensure_one()
        return {
            "id": self.id,
            "name": self.name,
            "device_code": self.device_id.code,
            "device_label": self.device_label or "",
            "owner_name": self.user_id.name,
            "last_seen": fields.Datetime.to_string(self.last_seen),
            "is_online": self._is_online(),
        }
