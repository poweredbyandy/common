from odoo import models
from odoo.tools.mail import plaintext2html


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def l10n_ve_report_line_description(self):
        self.ensure_one()
        description = super().l10n_ve_report_line_description()
        if self.display_type or self.is_downpayment or self.product_type == "combo":
            return description
        if not self.product_id:
            return description
        lang = self.order_id._get_lang()
        product = self.product_id.with_context(lang=lang, display_default_code=False)
        text = (product.name or "").strip()
        return plaintext2html(text, with_paragraph=False) if text else description
