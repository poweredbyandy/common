from odoo import fields, models


class ResUsersSettings(models.Model):
    _inherit = "res.users.settings"

    pba_sidebar_app_order = fields.Json(
        string="PBA Sidebar App Order",
        readonly=True,
    )
