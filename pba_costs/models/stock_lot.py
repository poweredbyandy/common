from odoo import models


class StockLot(models.Model):
    _name = "stock.lot"
    _inherit = ["stock.lot", "pba.cost.currency.mixin"]

    def _change_standard_price(self, new_price):
        company = self.env.company
        needs = self.filtered(lambda lot: lot._pba_cost_currency_differs_company(company))
        other = self - needs
        if other:
            super(StockLot, other)._change_standard_price(new_price)
        for lot in needs:
            company_price = lot._pba_amount_cost_to_company(
                new_price,
                company=company,
            )
            super(StockLot, lot)._change_standard_price(company_price)
            product = lot.product_id.with_company(company).with_context(
                disable_auto_svl=True
            )
            if product.cost_method != "standard" and product.quantity_svl:
                product._pba_standard_prices_to_cost_currency(company=company)
