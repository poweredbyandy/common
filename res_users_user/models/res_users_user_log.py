from odoo import fields, models


class ResUsersUserLog(models.Model):
    _name = "res.users.user.log"
    _description = "Sub-User Audit Log"
    _order = "date desc, id desc"

    sub_user_id = fields.Many2one(
        "res.users.user",
        required=True,
        ondelete="cascade",
        index=True,
    )
    user_id = fields.Many2one(
        "res.users",
        required=True,
        ondelete="cascade",
        index=True,
    )
    model = fields.Char(required=True, index=True)
    res_id = fields.Integer(required=True, index=True)
    method = fields.Selection(
        selection=[
            ("create", "Create"),
            ("write", "Write"),
        ],
        required=True,
    )
    date = fields.Datetime(
        default=fields.Datetime.now,
        required=True,
        index=True,
    )
    res_name = fields.Char()
