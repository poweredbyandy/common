from odoo import fields, models
from odoo.tools.float_utils import float_is_zero


class StockMove(models.Model):
    _inherit = "stock.move"

    def _pba_moves_for_avco_currency_align(self):
        return self.filtered(
            lambda move: move._is_in()
            and move.with_company(move.company_id).product_id.cost_method != "standard"
            and move.product_id._pba_cost_currency_differs_company(move.company_id)
        )

    def _pba_convert_date_for_move(self):
        self.ensure_one()
        if self.state == "done" and self.date:
            return self.date.date() if hasattr(self.date, "date") else self.date
        return fields.Date.context_today(self)

    def product_price_update_before_done(self, forced_qty=None):
        align_moves = self._pba_moves_for_avco_currency_align()
        by_company = {}
        for move in align_moves:
            by_company.setdefault(move.company_id, self.env["stock.move"])
            by_company[move.company_id] |= move

        prepared = []
        for company, company_moves in by_company.items():
            conv_date = company_moves[:1]._pba_convert_date_for_move()
            products = company_moves.mapped("product_id")
            lots = self.env["stock.lot"]
            for move in company_moves:
                if move.product_id.lot_valuated:
                    lots |= move.lot_ids
            products._pba_standard_prices_to_company_currency(
                company=company,
                conv_date=conv_date,
            )
            lots._pba_standard_prices_to_company_currency(
                company=company,
                conv_date=conv_date,
            )
            prepared.append((company, products, lots, conv_date))

        try:
            return super().product_price_update_before_done(forced_qty=forced_qty)
        finally:
            for company, products, lots, conv_date in prepared:
                products._pba_standard_prices_to_cost_currency(
                    company=company,
                    conv_date=conv_date,
                )
                lots._pba_standard_prices_to_cost_currency(
                    company=company,
                    conv_date=conv_date,
                )

    def _product_price_update_after_done(self):
        super()._product_price_update_after_done()
        for product, layers in self.stock_valuation_layer_ids.grouped(
            "product_id"
        ).items():
            if all(not move._is_out() for move in layers.stock_move_id):
                continue
            if not product.lot_valuated:
                continue
            company = layers.company_id
            if layers.with_company(company).product_id.cost_method == "standard":
                continue
            if product._pba_cost_currency_differs_company(company):
                product.with_company(company)._pba_sync_standard_price_from_svl(
                    company=company
                )

    def _get_price_unit(self):
        prices = super()._get_price_unit()
        self.ensure_one()
        if (
            self.origin_returned_move_id
            and self.origin_returned_move_id.sudo().stock_valuation_layer_ids
        ):
            return prices
        if self.purchase_line_id and not self._should_ignore_pol_price():
            return prices
        precision = self.env["decimal.precision"].precision_get("Product Price")
        if not float_is_zero(self.price_unit, precision) or self._should_force_price_unit():
            return prices
        product = self.product_id.with_company(self.company_id)
        if not product._pba_cost_currency_differs_company(self.company_id):
            return prices
        conv_date = self._pba_convert_date_for_move()
        converted = {}
        for lot, price in prices.items():
            if lot:
                converted[lot] = lot._pba_amount_cost_to_company(
                    price,
                    company=self.company_id,
                    conv_date=conv_date,
                )
            else:
                converted[lot] = product._pba_amount_cost_to_company(
                    price,
                    company=self.company_id,
                    conv_date=conv_date,
                )
        return converted

    def _get_in_svl_vals(self, forced_quantity):
        standard_moves = self.filtered(
            lambda m: m.product_id.cost_method == "standard"
            and m.product_id._pba_cost_currency_differs_company(m.company_id)
        )
        prepared = []
        for company, company_moves in standard_moves.grouped("company_id").items():
            products = company_moves.mapped("product_id")
            lots = self.env["stock.lot"]
            for move in company_moves:
                if move.product_id.lot_valuated:
                    lots |= move.lot_ids
            products._pba_standard_prices_to_company_currency(company=company)
            lots._pba_standard_prices_to_company_currency(company=company)
            prepared.append((company, products, lots))
        try:
            return super()._get_in_svl_vals(forced_quantity)
        finally:
            for company, products, lots in prepared:
                products._pba_standard_prices_to_cost_currency(company=company)
                lots._pba_standard_prices_to_cost_currency(company=company)
