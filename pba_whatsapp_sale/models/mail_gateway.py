from odoo import models

from .pba_whatsapp_templates import SALE_COMPANY_FIELDS, SALE_TEMPLATES


class MailGateway(models.Model):
    _inherit = "mail.gateway"

    def _pba_whatsapp_template_specs(self):
        specs = super()._pba_whatsapp_template_specs()
        specs.append(
            {
                "module": "pba_whatsapp_sale",
                "templates": SALE_TEMPLATES,
                "company_fields": SALE_COMPANY_FIELDS,
            }
        )
        return specs
