from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def l10n_ve_report_line_description(self):
        self.ensure_one()
        description = super().l10n_ve_report_line_description()
        if not self.product_id:
            return description
        lang = self.move_id.partner_id.lang or self.env.lang
        product = self.product_id.with_context(lang=lang, display_default_code=False)
        return (product.name or "").strip() or description
