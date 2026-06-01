from odoo import models
from odoo.tools.mail import plaintext2html


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    def _pba_build_product_line_text(self, product_name):
        line_parts = [line.strip() for line in (self.name or "").splitlines() if line.strip()]
        if not line_parts:
            return product_name
        first_line = line_parts[0]
        if first_line.startswith("[") and "]" in first_line:
            first_line = first_line.split("]", 1)[1].strip()
        remaining_lines = line_parts[1:]
        if product_name:
            first_lower = first_line.casefold()
            product_lower = product_name.casefold()
            if first_lower == product_lower:
                description_lines = remaining_lines
            elif first_lower.startswith(product_lower + " "):
                first_extra = first_line[len(product_name) :].strip()
                description_lines = (
                    ([first_extra] if first_extra else []) + remaining_lines
                )
            else:
                description_lines = [first_line] + remaining_lines
        else:
            description_lines = [first_line] + remaining_lines
        line_description = "\n".join(line for line in description_lines if line).strip()
        if not line_description:
            return product_name
        if product_name:
            return f"{product_name}\n{line_description}".strip()
        return line_description

    def l10n_ve_report_line_description(self):
        self.ensure_one()
        if self.display_type or self.is_downpayment or self.product_type == "combo":
            return super().l10n_ve_report_line_description()
        product_name = ""
        if self.product_id:
            lang = self.order_id._get_lang()
            product = self.product_id.with_context(lang=lang, display_default_code=False)
            product_name = (product.name or "").strip()
        text = self._pba_build_product_line_text(product_name)
        if not text:
            return super().l10n_ve_report_line_description()
        return plaintext2html(text, with_paragraph=False)
