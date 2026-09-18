from odoo import api, models


class IrConfigParameter(models.Model):
    _inherit = "ir.config_parameter"

    @api.model
    def get_web_dialog_size_config(self):
        result = super().get_web_dialog_size_config()
        result["default_maximize"] = bool(self.env.user.dialog_default_maximize)
        return result
