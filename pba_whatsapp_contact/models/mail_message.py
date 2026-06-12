from odoo import fields, models


class MailMessage(models.Model):
    _inherit = "mail.message"

    pba_whatsapp_template_id = fields.Many2one(
        "mail.whatsapp.template",
        string="Plantilla WhatsApp PBA",
        index=True,
        ondelete="set null",
    )
