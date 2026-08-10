from odoo import api, fields, models
from odoo.addons.mail.tools.discuss import Store


class MailMessage(models.Model):
    _inherit = "mail.message"

    sub_user_id = fields.Many2one(
        "res.users.user",
        string="Sub-User",
        index=True,
        ondelete="set null",
    )
    sub_user_name = fields.Char(related="sub_user_id.name")

    @api.model_create_multi
    def create(self, vals_list):
        sub_user_id = self.env.context.get("sub_user_id")
        if sub_user_id:
            for vals in vals_list:
                vals.setdefault("sub_user_id", sub_user_id)
        return super().create(vals_list)

    def _extras_to_store(self, store: Store, format_reply):
        super()._extras_to_store(store, format_reply)
        for message in self:
            store.add(
                message,
                {
                    "sub_user_id": message.sub_user_id.id,
                    "sub_user_name": message.sub_user_id.name or False,
                },
            )
