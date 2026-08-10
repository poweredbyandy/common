from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.translate import _


class ResUsersUser(models.Model):
    _name = "res.users.user"
    _description = "Sub-User"
    _order = "name, id"

    name = fields.Char(
        related="employee_id.name",
        store=True,
        readonly=True,
    )
    user_id = fields.Many2one(
        "res.users",
        required=True,
        ondelete="cascade",
        index=True,
    )
    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        ondelete="restrict",
        index=True,
    )
    active = fields.Boolean(default=True)
    pin = fields.Char(
        compute="_compute_pin",
        inverse="_inverse_pin",
        readonly=False,
    )
    company_id = fields.Many2one(
        related="user_id.company_id",
        store=True,
    )

    _sql_constraints = [
        (
            "user_employee_uniq",
            "unique(user_id, employee_id)",
            "This employee is already linked as a sub-user of this user.",
        ),
    ]

    @api.depends("employee_id")
    def _compute_pin(self):
        for sub_user in self:
            sub_user.pin = sub_user.employee_id.sudo().pin or False

    def _inverse_pin(self):
        for sub_user in self:
            sub_user._set_employee_pin(sub_user.pin)

    def _get_employee_pin(self):
        self.ensure_one()
        return self.employee_id.sudo().pin or False

    def _set_employee_pin(self, pin):
        self.ensure_one()
        if not self.employee_id:
            return
        if pin in (None, False, ""):
            return
        pin = str(pin)
        if not pin.isdigit():
            raise ValidationError(_("The PIN must contain only digits."))
        self.employee_id.sudo().write({"pin": pin})
        self.invalidate_recordset(["pin"])

    @api.model_create_multi
    def create(self, vals_list):
        prepared = []
        for vals in vals_list:
            vals = dict(vals)
            pin = vals.pop("pin", None)
            employee_id = vals.get("employee_id")
            if pin not in (None, False, "") and employee_id:
                pin = str(pin)
                if not pin.isdigit():
                    raise ValidationError(_("The PIN must contain only digits."))
                self.env["hr.employee"].browse(employee_id).sudo().write({
                    "pin": pin,
                })
            prepared.append(vals)
        return super().create(prepared)

    def write(self, vals):
        vals = dict(vals)
        pin = vals.pop("pin", None) if "pin" in vals else None
        result = super().write(vals)
        if pin not in (None, False, ""):
            for record in self:
                record._set_employee_pin(pin)
        return result

    @api.constrains("active", "employee_id")
    def _check_pin_required(self):
        for sub_user in self:
            if sub_user.active and not sub_user._get_employee_pin():
                raise ValidationError(
                    _(
                        "Employee %(employee)s must have a PIN to be used as an "
                        "active sub-user. Set it on the PIN field of this "
                        "sub-user."
                    )
                    % {"employee": sub_user.employee_id.display_name}
                )

    def _check_pin(self, pin):
        self.ensure_one()
        if not self.active:
            raise UserError(_("This sub-user is archived."))
        employee_pin = self._get_employee_pin()
        if not employee_pin or str(pin or "") != str(employee_pin):
            raise UserError(_("Incorrect PIN."))
        return True

    @api.model
    def _get_session_sub_users(self):
        return self.search([
            ("user_id", "=", self.env.user.id),
            ("active", "=", True),
        ])
