from odoo import models

from odoo.addons.mail.tools.discuss import Store


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    def _pba_get_whatsapp_customer_partner(self):
        self.ensure_one()
        gateway_partner_ids = self.gateway_id.member_ids.partner_id.ids
        return self.channel_member_ids.partner_id.filtered(
            lambda partner, gw_ids=gateway_partner_ids: partner.id not in gw_ids
        )[:1]

    def _pba_get_last_attending_partner(self):
        self.ensure_one()
        customer = self._pba_get_whatsapp_customer_partner()
        domain = [
            ("model", "=", "discuss.channel"),
            ("res_id", "=", self.id),
            ("message_type", "=", "comment"),
            ("author_id", "!=", False),
        ]
        if customer:
            domain.append(("author_id", "!=", customer.id))
        last_message = self.env["mail.message"].search(
            domain, order="date desc, id desc", limit=1
        )
        if last_message:
            return last_message.author_id
        if (
            "whatsapp_assigned_user_id" in self._fields
            and self.whatsapp_assigned_user_id
        ):
            return self.whatsapp_assigned_user_id.partner_id
        return False

    def _pba_get_gateway_store_vals(self):
        self.ensure_one()
        operator_partner = self._pba_get_last_attending_partner()
        return {
            "operator": (
                Store.one(operator_partner, fields=["name"])
                if operator_partner
                else False
            ),
        }

    def _pba_broadcast_gateway_store(self):
        for channel in self.filtered(lambda c: c.channel_type == "gateway"):
            channel._bus_send_store(channel, channel._pba_get_gateway_store_vals())

    def _to_store(self, store: Store):
        result = super()._to_store(store)
        for channel in self.filtered(lambda c: c.channel_type == "gateway"):
            store.add(channel, channel._pba_get_gateway_store_vals())
        return result

    def _notify_thread(self, message, msg_vals=False, **kwargs):
        rdata = super()._notify_thread(message, msg_vals=msg_vals, **kwargs)
        self.filtered(lambda c: c.channel_type == "gateway")._pba_broadcast_gateway_store()
        return rdata

    def _message_post_after_hook(self, message, msg_vals):
        res = super()._message_post_after_hook(message, msg_vals)
        self.filtered(lambda c: c.channel_type == "gateway")._pba_broadcast_gateway_store()
        return res
