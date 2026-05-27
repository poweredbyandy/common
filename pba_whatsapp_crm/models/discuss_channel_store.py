from odoo import models

from odoo.addons.mail.tools.discuss import Store


class DiscussChannelStore(models.Model):
    _inherit = "discuss.channel"

    def _to_store(self, store: Store):
        result = super()._to_store(store)
        for channel in self.filtered(lambda c: c.channel_type == "gateway"):
            crm_seller_partner = channel.whatsapp_lead_id.user_id.partner_id
            if crm_seller_partner:
                store.add(channel, {"crm_seller": Store.one(crm_seller_partner)})
        return result
