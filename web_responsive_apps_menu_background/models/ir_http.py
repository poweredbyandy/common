from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        result = super().session_info()
        result["apps_menu_background"] = self.env.company._get_apps_menu_background_info()
        return result
