from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    numeric_focus_select = fields.Boolean(
        string="Seleccionar números al enfocar",
        default=True,
        help="Si está activo, al entrar en un campo entero o decimal se "
        "selecciona todo su valor y lo que se escriba lo reemplaza.",
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["numeric_focus_select"]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ["numeric_focus_select"]
