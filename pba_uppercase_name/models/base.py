from odoo import api, models
from odoo.fields import Command

_PBA_UPPERCASE_NAME_SKIP_MODELS = frozenset({
    "res.lang",
    "base.language.install",
})


class Base(models.AbstractModel):
    _inherit = "base"

    @api.model
    def _pba_should_uppercase_name(self):
        if self._name in _PBA_UPPERCASE_NAME_SKIP_MODELS:
            return False
        return not self.is_transient()

    @api.model
    def _pba_uppercase_name_value(self, value):
        if isinstance(value, str):
            return value.upper()
        if isinstance(value, dict):
            return {
                key: (item.upper() if isinstance(item, str) else item)
                for key, item in value.items()
            }
        return value

    @api.model
    def _pba_uppercase_name_in_vals(self, vals):
        if not vals or not self._pba_should_uppercase_name():
            return
        name_field = self._fields.get("name")
        if name_field and name_field.type in ("char", "text") and "name" in vals:
            vals["name"] = self._pba_uppercase_name_value(vals["name"])
        for field_name, field_value in vals.items():
            field = self._fields.get(field_name)
            if not field or field.type != "one2many" or not isinstance(field_value, list):
                continue
            comodel = self.env[field.comodel_name]
            for command in field_value:
                if not isinstance(command, (list, tuple)) or len(command) < 3:
                    continue
                if command[0] in (Command.CREATE, Command.UPDATE):
                    comodel._pba_uppercase_name_in_vals(command[2])

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._pba_uppercase_name_in_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._pba_uppercase_name_in_vals(vals)
        return super().write(vals)
