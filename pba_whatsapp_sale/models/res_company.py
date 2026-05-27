from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    whatsapp_template_sale_quotation_id = fields.Many2one(
        "mail.whatsapp.template",
        string="Plantilla presupuesto",
        domain=[("gateway_id.gateway_type", "=", "whatsapp")],
    )
    whatsapp_template_sale_confirmed_id = fields.Many2one(
        "mail.whatsapp.template",
        string="Plantilla pedido confirmado",
        domain=[("gateway_id.gateway_type", "=", "whatsapp")],
    )
    whatsapp_template_delivery_done_id = fields.Many2one(
        "mail.whatsapp.template",
        string="Plantilla entrega realizada",
        domain=[("gateway_id.gateway_type", "=", "whatsapp")],
    )
