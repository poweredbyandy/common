from odoo import _, api, fields, models


class PbaWhatsappAutoreplyConfig(models.Model):
    _name = "pba.whatsapp.autoreply.config"
    _description = "Configuración de respuestas automáticas WhatsApp"

    company_id = fields.Many2one(
        "res.company",
        required=True,
        ondelete="cascade",
        default=lambda self: self.env.company,
    )
    whatsapp_autoreply_enabled = fields.Boolean(
        related="company_id.whatsapp_autoreply_enabled",
        readonly=False,
    )
    whatsapp_autoreply_default_message = fields.Text(
        related="company_id.whatsapp_autoreply_default_message",
        readonly=False,
    )
    whatsapp_autoreply_rule_ids = fields.One2many(
        related="company_id.whatsapp_autoreply_rule_ids",
        readonly=False,
    )

    _sql_constraints = [
        (
            "company_uniq",
            "unique(company_id)",
            "Solo puede existir una configuración por compañía.",
        )
    ]

    @api.model
    def _pba_get_company_config(self, company=None):
        company = company or self.env.company
        config = self.search([("company_id", "=", company.id)], limit=1)
        if not config:
            config = self.create({"company_id": company.id})
        return config

    @api.model
    def action_open_autoreply(self):
        config = self._pba_get_company_config()
        return {
            "type": "ir.actions.act_window",
            "name": _("Respuestas automáticas"),
            "res_model": "pba.whatsapp.autoreply.config",
            "res_id": config.id,
            "view_mode": "form",
            "target": "current",
        }
