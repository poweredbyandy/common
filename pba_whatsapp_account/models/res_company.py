from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    whatsapp_template_overdue_id = fields.Many2one(
        "mail.whatsapp.template",
        string="Plantilla cuenta vencida",
        domain=[("gateway_id.gateway_type", "=", "whatsapp")],
    )
    whatsapp_overdue_auto_send = fields.Boolean(
        string="Enviar recordatorio automático de mora",
        default=False,
    )
    whatsapp_overdue_days = fields.Integer(
        string="Días de mora mínimos",
        default=1,
    )
