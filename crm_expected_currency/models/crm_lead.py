from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    expected_currency_id = fields.Many2one(
        "res.currency",
        string="Moneda del ingreso esperado",
        default=lambda self: self._default_expected_currency(),
    )
    expected_revenue_currency = fields.Monetary(
        string="Ingreso esperado",
        currency_field="expected_currency_id",
        default=0.0,
    )

    @api.model
    def _default_expected_currency(self):
        company = self.env.company
        return company.crm_expected_currency_id or company.currency_id

    def _expected_company(self):
        self.ensure_one()
        return self.company_id or self.env.company

    def _convert_expected(self, amount, from_currency, to_currency):
        self.ensure_one()
        amount = amount or 0.0
        company = self._expected_company()
        if not from_currency or not to_currency or from_currency == to_currency:
            return amount
        return from_currency._convert(
            amount,
            to_currency,
            company,
            fields.Date.context_today(self),
        )

    def _sync_from_currency_amount(self):
        for lead in self:
            currency = lead.expected_currency_id or lead.company_currency
            company_currency = lead.company_currency
            amount = lead._convert_expected(
                lead.expected_revenue_currency, currency, company_currency,
            )
            if not company_currency or company_currency.compare_amounts(lead.expected_revenue, amount):
                lead.with_context(skip_expected_currency_sync=True).write({
                    "expected_revenue": amount,
                })

    def _sync_from_company_amount(self):
        for lead in self:
            currency = lead.expected_currency_id or lead.company_currency
            company_currency = lead.company_currency
            amount = lead._convert_expected(
                lead.expected_revenue, company_currency, currency,
            )
            vals = {"expected_revenue_currency": amount}
            if currency and lead.expected_currency_id != currency:
                vals["expected_currency_id"] = currency.id
            lead.with_context(skip_expected_currency_sync=True).write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("skip_expected_currency_sync"):
            for vals in vals_list:
                self._prepare_expected_currency_vals(vals)
        return super().create(vals_list)

    def write(self, vals):
        if self.env.context.get("skip_expected_currency_sync"):
            return super().write(vals)
        res = super().write(vals)
        if "expected_revenue_currency" in vals or "expected_currency_id" in vals:
            self._sync_from_currency_amount()
        elif "expected_revenue" in vals:
            self._sync_from_company_amount()
        return res

    @api.model
    def _prepare_expected_currency_vals(self, vals):
        company = (
            self.env["res.company"].browse(vals["company_id"])
            if vals.get("company_id") else self.env.company
        )
        company_currency = company.currency_id
        if vals.get("expected_currency_id"):
            currency = self.env["res.currency"].browse(vals["expected_currency_id"])
        else:
            currency = company.crm_expected_currency_id or company_currency
            vals["expected_currency_id"] = currency.id
        today = fields.Date.context_today(self)
        if "expected_revenue_currency" in vals:
            amount = vals.get("expected_revenue_currency") or 0.0
            if currency and company_currency and currency != company_currency:
                amount = currency._convert(amount, company_currency, company, today)
            vals["expected_revenue"] = amount
        elif "expected_revenue" in vals:
            amount = vals.get("expected_revenue") or 0.0
            if currency and company_currency and currency != company_currency:
                amount = company_currency._convert(amount, currency, company, today)
            vals["expected_revenue_currency"] = amount
