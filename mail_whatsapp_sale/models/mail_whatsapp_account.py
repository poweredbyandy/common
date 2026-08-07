from odoo import api, models


class MailWhatsappAccount(models.Model):
    _inherit = "mail.whatsapp.account"

    @api.model
    def ensure_demo_account(self):
        account = super().ensure_demo_account()
        self.env["mail.whatsapp.template"]._ensure_sale_whatsapp_templates(account)
        return account
