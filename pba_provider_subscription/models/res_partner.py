from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    pba_portal_user_ids = fields.One2many(
        "res.users",
        "partner_id",
        string="Portal Users",
        domain=[("share", "=", True)],
    )

    def action_pba_generate_subscription_api_key(self):
        self.ensure_one()
        partner = self.commercial_partner_id
        return {
            "type": "ir.actions.act_window",
            "name": "Generar API Key del cliente",
            "res_model": "pba.subscription.api.key.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_partner_id": partner.id,
            },
        }
