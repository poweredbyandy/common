from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class ProductProduct(models.Model):
    _inherit = "product.product"

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        products._share_standard_price_across_companies()
        return products

    def write(self, vals):
        res = super().write(vals)
        if "standard_price" in vals:
            self._share_standard_price_across_companies()
        return res

    def action_share_standard_price_across_companies(self):
        to_share = self.filtered(lambda product: not product.company_id)
        if not to_share:
            raise UserError(
                _("Solo se puede replicar el costo en productos sin empresa.")
            )
        to_share._share_standard_price_across_companies()
        skipped = len(self) - len(to_share)
        message = _(
            "Se replicó el costo de %(company)s a las demás compañías.",
            company=self.env.company.display_name,
        )
        if skipped:
            message = _(
                "%(message)s Se omitieron %(count)s producto(s) con empresa.",
                message=message,
                count=skipped,
            )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Costo replicado"),
                "message": message,
                "type": "success",
                "sticky": False,
            },
        }

    def _product_cost_multi_company_targets(self):
        return self.env["res.company"].sudo().search([])

    def _product_cost_share_convert(self, amount, from_company, to_company):
        self.ensure_one()
        if from_company == to_company:
            return amount
        from_currency = self.with_company(from_company).cost_currency_id
        to_currency = self.with_company(to_company).cost_currency_id
        if not from_currency or not to_currency or from_currency == to_currency:
            return amount
        return from_currency._convert(
            amount,
            to_currency,
            to_company,
            fields.Date.context_today(self),
        )

    def _share_standard_price_across_companies(self):
        if self.env.context.get("skip_product_cost_multi_company"):
            return
        to_share = self.filtered(lambda product: not product.company_id)
        if not to_share:
            return
        source_company = self.env.company
        other_companies = self._product_cost_multi_company_targets() - source_company
        if not other_companies:
            return
        digits = self.env["decimal.precision"].precision_get("Product Price")
        for product in to_share:
            amount = product.standard_price
            for company in other_companies:
                converted = product._product_cost_share_convert(
                    amount,
                    source_company,
                    company,
                )
                product_company = product.with_company(company).sudo()
                if (
                    float_compare(
                        product_company.standard_price,
                        converted,
                        precision_digits=digits,
                    )
                    == 0
                ):
                    continue
                product_company.with_context(
                    skip_product_cost_multi_company=True,
                ).write({"standard_price": converted})
