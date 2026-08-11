# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.tools.float_utils import float_is_zero


class PbaCostCurrencyMixin(models.AbstractModel):
    _name = "pba.cost.currency.mixin"
    _description = "Helpers cost currency vs company currency (PBA)"

    def _pba_cost_currency(self):
        self.ensure_one()
        if self._name == "stock.lot":
            product = self.product_id
            if product.cost_currency_id:
                return product.cost_currency_id
            return self._pba_cost_company().currency_id
        if "cost_currency_id" in self._fields and self.cost_currency_id:
            return self.cost_currency_id
        return self._pba_cost_company().currency_id

    def _pba_cost_company(self):
        self.ensure_one()
        if "company_id" in self._fields and self.company_id:
            return self.company_id
        return self.env.company

    def _pba_cost_currency_differs_company(self, company=None):
        self.ensure_one()
        company = company or self._pba_cost_company()
        cost_currency = self._pba_cost_currency()
        return bool(
            company
            and company.currency_id
            and cost_currency
            and cost_currency != company.currency_id
        )

    def _pba_cost_convert_date(self, company=None):
        self.ensure_one()
        return fields.Date.context_today(
            self.with_company(company or self._pba_cost_company())
        )

    def _pba_amount_cost_to_company(self, amount, company=None, conv_date=None):
        self.ensure_one()
        company = company or self._pba_cost_company()
        cost_currency = self._pba_cost_currency()
        if (
            not company
            or not company.currency_id
            or not cost_currency
            or cost_currency == company.currency_id
        ):
            return float(amount or 0.0)
        return cost_currency._convert(
            float(amount or 0.0),
            company.currency_id,
            company,
            conv_date or self._pba_cost_convert_date(company),
            round=False,
        )

    def _pba_amount_company_to_cost(self, amount, company=None, conv_date=None):
        self.ensure_one()
        company = company or self._pba_cost_company()
        cost_currency = self._pba_cost_currency()
        if (
            not company
            or not company.currency_id
            or not cost_currency
            or cost_currency == company.currency_id
        ):
            return float(amount or 0.0)
        return company.currency_id._convert(
            float(amount or 0.0),
            cost_currency,
            company,
            conv_date or self._pba_cost_convert_date(company),
            round=False,
        )

    def _pba_write_standard_price(self, price, company=None):
        company = company or self._pba_cost_company()
        self.with_company(company).with_context(disable_auto_svl=True).sudo().write(
            {"standard_price": price}
        )

    def _pba_standard_prices_to_company_currency(self, company=None, conv_date=None):
        for record in self:
            rec_company = company or record._pba_cost_company()
            if not record._pba_cost_currency_differs_company(rec_company):
                continue
            company_price = record._pba_amount_cost_to_company(
                record.with_company(rec_company).standard_price,
                company=rec_company,
                conv_date=conv_date,
            )
            record._pba_write_standard_price(company_price, company=rec_company)

    def _pba_standard_prices_to_cost_currency(self, company=None, conv_date=None):
        for record in self:
            rec_company = company or record._pba_cost_company()
            if not record._pba_cost_currency_differs_company(rec_company):
                continue
            cost_price = record._pba_amount_company_to_cost(
                record.with_company(rec_company).standard_price,
                company=rec_company,
                conv_date=conv_date,
            )
            record._pba_write_standard_price(cost_price, company=rec_company)

    def _pba_sync_standard_price_from_svl(self, company=None, conv_date=None):
        for record in self:
            rec_company = company or record._pba_cost_company()
            if record._name == "stock.lot":
                uom = record.product_id.uom_id
                quantity_svl = record.sudo().with_company(rec_company).quantity_svl
                value_svl = record.sudo().with_company(rec_company).value_svl
            else:
                uom = record.uom_id
                quantity_svl = record.sudo().with_company(rec_company).quantity_svl
                value_svl = record.sudo().with_company(rec_company).value_svl
            if float_is_zero(quantity_svl, precision_rounding=uom.rounding):
                continue
            company_price = value_svl / quantity_svl
            if record._pba_cost_currency_differs_company(rec_company):
                price = record._pba_amount_company_to_cost(
                    company_price,
                    company=rec_company,
                    conv_date=conv_date,
                )
            else:
                price = company_price
            record._pba_write_standard_price(price, company=rec_company)
