from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        result = super().session_info()
        result["numeric_focus_select"] = bool(self.env.user.numeric_focus_select)
        return result
