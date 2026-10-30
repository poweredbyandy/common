from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MailWhatsappAssign(models.TransientModel):
    _name = "mail.whatsapp.assign"
    _description = "Assign WhatsApp Chats"

    channel_ids = fields.Many2many(
        "discuss.channel",
        "mail_whatsapp_assign_channel_rel",
        "wizard_id",
        "channel_id",
        string="Chats",
        required=True,
        domain=[("channel_type", "=", "whatsapp")],
    )
    allowed_user_ids = fields.Many2many(
        "res.users",
        compute="_compute_allowed_user_ids",
    )
    user_id = fields.Many2one(
        "res.users",
        string="Responsible",
        domain="[('id', 'in', allowed_user_ids)]",
        help="Agent who will handle the selected chats. Leave it empty to "
        "release them so any agent can take them.",
    )

    @api.depends("channel_ids")
    def _compute_allowed_user_ids(self):
        users_model = self.env["res.users"]
        for wizard in self:
            allowed = None
            for channel in wizard.channel_ids:
                channel_users = users_model.browse(
                    [user["id"] for user in channel.whatsapp_get_assignable_users()]
                )
                allowed = channel_users if allowed is None else allowed & channel_users
            wizard.allowed_user_ids = allowed or users_model

    def action_assign(self):
        self.ensure_one()
        if self.user_id and self.user_id not in self.allowed_user_ids:
            raise UserError(
                _(
                    "%(user)s cannot be assigned to every selected chat. "
                    "Select chats of the same WhatsApp account.",
                    user=self.user_id.name,
                )
            )
        for channel in self.channel_ids:
            channel.whatsapp_set_responsible(self.user_id.id or False)
        return {"type": "ir.actions.act_window_close"}
