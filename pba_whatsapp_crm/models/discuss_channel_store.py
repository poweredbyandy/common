from odoo import models

from odoo.addons.mail.tools.discuss import Store


class DiscussChannelStore(models.Model):
    _inherit = "discuss.channel"

    def _pba_get_crm_seller_partner(self):
        self.ensure_one()
        channel = self.sudo()
        seller_user = False
        if channel.whatsapp_lead_id and channel.whatsapp_lead_id.user_id:
            seller_user = channel.whatsapp_lead_id.user_id
        elif channel.whatsapp_assigned_user_id:
            seller_user = channel.whatsapp_assigned_user_id
        return seller_user.partner_id if seller_user else False

    def _pba_get_gateway_store_vals(self):
        vals = super()._pba_get_gateway_store_vals()
        crm_seller_partner = self._pba_get_crm_seller_partner()
        vals.update(
            {
                "whatsapp_crm_lead_count": self._pba_count_whatsapp_crm_leads(),
                "crm_seller": (
                    Store.one(crm_seller_partner, fields=["name"])
                    if crm_seller_partner
                    else False
                ),
            }
        )
        return vals
