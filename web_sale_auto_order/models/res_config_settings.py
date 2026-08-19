from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    auto_order_pricelist_id = fields.Many2one(
        comodel_name="product.pricelist",
        related="website_id.auto_order_pricelist_id",
        readonly=False,
        string="Auto Order Pricelist",
    )
    auto_order_button_color = fields.Char(
        related="website_id.auto_order_button_color",
        readonly=False,
        string="Button Color",
    )
    auto_order_button_text_color = fields.Char(
        related="website_id.auto_order_button_text_color",
        readonly=False,
        string="Button Text Color",
    )
    auto_order_success_message = fields.Text(
        related="website_id.auto_order_success_message",
        readonly=False,
        string="Success Extra Message",
    )
    auto_order_lang_id = fields.Many2one(
        related="website_id.auto_order_lang_id",
        readonly=False,
        string="Kiosk Language",
    )
