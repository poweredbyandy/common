from odoo import models

from .pba_whatsapp_templates import ACCOUNT_COMPANY_FIELDS, ACCOUNT_TEMPLATES


class MailGateway(models.Model):
    _inherit = "mail.gateway"

    def _pba_whatsapp_template_specs(self):
        specs = super()._pba_whatsapp_template_specs()
        specs.append(
            {
                "module": "pba_whatsapp_account",
                "templates": ACCOUNT_TEMPLATES,
                "company_fields": ACCOUNT_COMPANY_FIELDS,
            }
        )
        return specs
