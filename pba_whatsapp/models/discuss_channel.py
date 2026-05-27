from odoo import models

from odoo.addons.mail.tools.discuss import Store


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    def _to_store(self, store: Store):
        result = super()._to_store(store)
        for channel in self.filtered(lambda c: c.channel_type == "gateway"):
            operator_partner = False
            if "whatsapp_assigned_user_id" in channel._fields:
                operator_partner = channel.whatsapp_assigned_user_id.partner_id
            if operator_partner:
                store.add(channel, {"operator": Store.one(operator_partner)})
        return result
