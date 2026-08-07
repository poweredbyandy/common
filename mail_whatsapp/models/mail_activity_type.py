from odoo import fields, models


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    is_whatsapp_followup = fields.Boolean(
        string="WhatsApp Follow-up",
        help="If enabled, Send Now and the due-date cron send WhatsApp "
        "instead of email, then mark the activity as done.",
    )
