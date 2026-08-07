from odoo import fields, models


class MailWhatsappTag(models.Model):
    _name = "mail.whatsapp.tag"
    _description = "WhatsApp Conversation Tag"
    _order = "name, id"

    name = fields.Char(required=True, translate=True)
    color = fields.Integer(string="Color Index", default=0)
    channel_ids = fields.Many2many(
        "discuss.channel",
        "mail_whatsapp_channel_tag_rel",
        "tag_id",
        "channel_id",
        string="Channels",
    )

    _sql_constraints = [
        ("name_uniq", "unique(name)", "Tag name must be unique."),
    ]
