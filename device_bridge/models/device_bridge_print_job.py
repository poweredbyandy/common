# -*- coding: utf-8 -*-
from odoo import api, fields, models


class DeviceBridgePrintJob(models.Model):
    _name = "device.bridge.print.job"
    _description = "Device Bridge Print Job"
    _order = "id desc"

    name = fields.Char(required=True)
    device_id = fields.Many2one(
        "device.bridge",
        required=True,
        ondelete="cascade",
        index=True,
    )
    gateway_id = fields.Many2one(
        "device.bridge.gateway",
        required=True,
        ondelete="cascade",
        index=True,
    )
    requester_id = fields.Many2one(
        "res.users",
        required=True,
        ondelete="cascade",
        index=True,
    )
    data_b64 = fields.Text(required=True)
    state = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("processing", "Processing"),
            ("done", "Done"),
            ("error", "Error"),
        ],
        default="pending",
        required=True,
        index=True,
    )
    error_message = fields.Char()
    company_id = fields.Many2one(
        "res.company",
        related="device_id.company_id",
        store=True,
        index=True,
    )

    def _to_payload(self):
        self.ensure_one()
        return {
            "id": self.id,
            "job_id": self.name,
            "device_code": self.device_id.code,
            "data_b64": self.data_b64,
            "state": self.state,
        }
