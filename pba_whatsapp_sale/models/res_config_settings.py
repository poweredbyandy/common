from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    whatsapp_template_sale_quotation_id = fields.Many2one(
        related="company_id.whatsapp_template_sale_quotation_id",
        readonly=False,
    )
    whatsapp_template_sale_confirmed_id = fields.Many2one(
        related="company_id.whatsapp_template_sale_confirmed_id",
        readonly=False,
    )
    whatsapp_template_delivery_done_id = fields.Many2one(
        related="company_id.whatsapp_template_delivery_done_id",
        readonly=False,
    )
