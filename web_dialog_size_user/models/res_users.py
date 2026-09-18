from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    dialog_default_maximize = fields.Boolean(
        string="Siempre expandir diálogos",
        default=False,
        help="Si está activo, los diálogos se abren maximizados.",
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["dialog_default_maximize"]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ["dialog_default_maximize"]
