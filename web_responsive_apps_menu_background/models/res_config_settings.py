from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    apps_menu_background_image = fields.Image(
        related="company_id.apps_menu_background_image",
        readonly=False,
    )
    apps_menu_background_size = fields.Integer(
        related="company_id.apps_menu_background_size",
        readonly=False,
    )
    apps_menu_background_size_preset = fields.Selection(
        related="company_id.apps_menu_background_size_preset",
        readonly=False,
    )
    apps_menu_background_position = fields.Selection(
        related="company_id.apps_menu_background_position",
        readonly=False,
    )
    apps_menu_background_opacity = fields.Integer(
        related="company_id.apps_menu_background_opacity",
        readonly=False,
    )
