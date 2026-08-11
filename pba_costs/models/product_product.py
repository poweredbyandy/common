from odoo import fields, models
from odoo.tools.float_utils import float_compare, float_is_zero


class ProductProduct(models.Model):
    _name = "product.product"
    _inherit = ["product.product", "pba.cost.currency.mixin"]

    pba_last_cost = fields.Monetary(
        related="product_tmpl_id.pba_last_cost",
        string="Último costo",
        currency_field="cost_currency_id",
        readonly=True,
    )
    pba_final_cost = fields.Monetary(
        related="product_tmpl_id.pba_final_cost",
        string="Costo final",
        currency_field="cost_currency_id",
        readonly=True,
    )

    def action_pba_last_cost_purchase_traceability(self):
        self.ensure_one()
        return self.product_tmpl_id.action_pba_last_cost_purchase_traceability()

    def action_pba_cost_history_freight(self):
        self.ensure_one()
        return self.product_tmpl_id.action_pba_cost_history_freight()

    def action_pba_cost_history_tariff(self):
        self.ensure_one()
        return self.product_tmpl_id.action_pba_cost_history_tariff()

    def action_pba_cost_history_operative(self):
        self.ensure_one()
        return self.product_tmpl_id.action_pba_cost_history_operative()

    def action_pba_cost_history_nationalization(self):
        self.ensure_one()
        return self.product_tmpl_id.action_pba_cost_history_nationalization()

    def _change_standard_price(self, new_price):
        same_currency = self.env["product.product"]
        for product in self:
            company = self.env.company
            if product._pba_cost_currency_differs_company(company):
                company_price = product._pba_amount_cost_to_company(
                    new_price,
                    company=company,
                )
                super(ProductProduct, product)._change_standard_price(company_price)
            else:
                same_currency |= product
        if same_currency:
            super(ProductProduct, same_currency)._change_standard_price(new_price)

    def _prepare_out_svl_vals(self, quantity, company, lot=False):
        self.ensure_one()
        to_convert = self.env["product.product"]
        lots = self.env["stock.lot"]
        if self._pba_cost_currency_differs_company(company):
            to_convert = self
        if lot and lot._pba_cost_currency_differs_company(company):
            lots = lot
        to_convert._pba_standard_prices_to_company_currency(company=company)
        lots._pba_standard_prices_to_company_currency(company=company)
        try:
            return super()._prepare_out_svl_vals(quantity, company, lot=lot)
        finally:
            to_convert._pba_standard_prices_to_cost_currency(company=company)
            lots._pba_standard_prices_to_cost_currency(company=company)

    def _run_fifo(self, quantity, company, lot=False):
        result = super()._run_fifo(quantity, company, lot=lot)
        if self.cost_method == "fifo" and self._pba_cost_currency_differs_company(
            company
        ):
            digits = self.env["decimal.precision"].precision_get("Product Price")
            product = self.with_company(company)
            quantity_svl = product.sudo().quantity_svl
            if not float_is_zero(quantity_svl, precision_rounding=product.uom_id.rounding):
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
            else:
                product._pba_standard_prices_to_cost_currency(company=company)
        return result

    def _run_fifo_vacuum(self, company=None):
        company = company or self.env.company
        result = super()._run_fifo_vacuum(company=company)
        digits = self.env["decimal.precision"].precision_get("Product Price")
        for product in self:
            if not product._pba_cost_currency_differs_company(company):
                continue
            product = product.with_company(company)
            quantity_svl = product.sudo().quantity_svl
            if float_is_zero(quantity_svl, precision_rounding=product.uom_id.rounding):
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
        return result
