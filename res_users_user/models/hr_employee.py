from odoo import api, fields, models
from odoo.tools.translate import _


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    sub_user_ids = fields.One2many(
        "res.users.user",
        "employee_id",
        string="Sub-Users",
    )
    sub_user_count = fields.Integer(compute="_compute_sub_user_count")

    @api.depends("sub_user_ids")
    def _compute_sub_user_count(self):
        for employee in self:
            employee.sub_user_count = len(employee.sub_user_ids)

    def action_view_sub_users(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Sub-Users"),
            "res_model": "res.users.user",
            "view_mode": "list,form",
            "domain": [("employee_id", "=", self.id)],
            "context": {"default_employee_id": self.id},
        }
