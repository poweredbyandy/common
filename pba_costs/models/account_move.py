from odoo import models
from odoo.tools.float_utils import float_compare, float_is_zero


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        res = super()._post(soft=soft)
        digits = self.env["decimal.precision"].precision_get("Product Price")
        for move in self:
            if move.move_type not in ("in_invoice", "in_refund", "in_receipt"):
                continue
            company = move.company_id
            products = move.invoice_line_ids.mapped("product_id").filtered(
                lambda p: p.cost_method in ("average", "fifo")
                and p._pba_cost_currency_differs_company(company)
            )
            for product in products:
                product = product.with_company(company)
                quantity_svl = product.sudo().quantity_svl
                if float_is_zero(
                    quantity_svl,
                    precision_rounding=product.uom_id.rounding,
                ):
                    continue
                company_avg = product.sudo().value_svl / quantity_svl
                if (
                    float_compare(
                        product.standard_price,
                        company_avg,
                        precision_digits=digits,
                    )
                    == 0
                ):
                    product._pba_standard_prices_to_cost_currency(company=company)
        return res
