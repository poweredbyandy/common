from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    risk_dashboard_json = fields.Json(compute="_compute_risk_dashboard_json")

    @api.onchange("risk_sale_order_include")
    def _onchange_pba_risk_sale_order_include(self):
        for partner in self:
            if partner.risk_sale_order_include and partner.credit_limit:
                partner.risk_sale_order_limit = partner.credit_limit

    @api.constrains("risk_sale_order_limit", "credit_limit")
    def _check_pba_risk_sale_order_limit(self):
        for partner in self:
            if (
                partner.credit_limit
                and partner.risk_sale_order_limit
                and partner.risk_sale_order_limit > partner.credit_limit
            ):
                raise ValidationError(
                    _(
                        "El limite de pedidos no puede ser superior al limite de credito."
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        prepared_vals_list = []
        force_vals_per_record = []
        risk_fields = {
            "credit_currency",
            "manual_credit_currency_id",
            "credit_limit",
            "risk_sale_order_include",
            "risk_sale_order_limit",
            "risk_invoice_draft_include",
            "risk_invoice_draft_limit",
            "risk_invoice_open_include",
            "risk_invoice_open_limit",
            "risk_invoice_unpaid_include",
            "risk_invoice_unpaid_limit",
            "risk_account_amount_include",
            "risk_account_amount_limit",
            "risk_account_amount_unpaid_include",
            "risk_account_amount_unpaid_limit",
        }
        for vals in vals_list:
            vals = dict(vals)
            force_vals = {}
            if not vals.get("parent_id"):
                company_id = vals.get("company_id") or self.env.company.id or self.env.user.company_id.id
                company = self.env["res.company"].browse(company_id) if company_id else self.env["res.company"].browse()
                settings = (
                    self.env["pba.financial.risk.global.settings"]
                    .sudo()
                    .get_or_create_for_company(company)
                )
                if settings:
                    global_vals = settings._get_partner_global_risk_vals()
                    for field_name, value in global_vals.items():
                        if field_name not in risk_fields:
                            continue
                        current_value = vals.get(field_name)
                        if field_name not in vals or current_value in (False, 0, 0.0, ""):
                            vals[field_name] = value
                            force_vals[field_name] = value
            prepared_vals_list.append(vals)
            force_vals_per_record.append(force_vals)
        records = super().create(prepared_vals_list)
        for record, force_vals in zip(records, force_vals_per_record):
            if not force_vals or record.parent_id:
                continue
            record.sudo().write(force_vals)
        return records

    @api.depends(
        "risk_currency_id",
        "risk_currency_id.symbol",
        "risk_currency_id.position",
        "credit_limit",
        "risk_total",
        "risk_remaining_value",
        "risk_remaining_percentage",
        "risk_invoice_draft",
        "risk_invoice_draft_limit",
        "risk_invoice_draft_include",
        "risk_invoice_open",
        "risk_invoice_open_limit",
        "risk_invoice_open_include",
        "risk_invoice_unpaid",
        "risk_invoice_unpaid_limit",
        "risk_invoice_unpaid_include",
        "risk_account_amount",
        "risk_account_amount_limit",
        "risk_account_amount_include",
        "risk_account_amount_unpaid",
        "risk_account_amount_unpaid_limit",
        "risk_account_amount_unpaid_include",
        "risk_sale_order",
        "risk_sale_order_limit",
        "risk_sale_order_include",
        "risk_allow_edit",
    )
    def _compute_risk_dashboard_json(self):
        for partner in self:
            currency = partner.risk_currency_id
            lines = [
                (
                    "Limite de Pedidos",
                    partner.risk_sale_order,
                    partner.risk_sale_order_limit,
                    partner.risk_sale_order_include,
                    "risk_sale_order_include",
                    "risk_sale_order_limit",
                ),
                (
                    "Limite de Facturas Borrador",
                    partner.risk_invoice_draft,
                    partner.risk_invoice_draft_limit,
                    partner.risk_invoice_draft_include,
                    "risk_invoice_draft_include",
                    "risk_invoice_draft_limit",
                ),
                (
                    "Limite de Facturas Abiertas",
                    partner.risk_invoice_open,
                    partner.risk_invoice_open_limit,
                    partner.risk_invoice_open_include,
                    "risk_invoice_open_include",
                    "risk_invoice_open_limit",
                ),
                (
                    "Limite de Facturas Vencidas",
                    partner.risk_invoice_unpaid,
                    partner.risk_invoice_unpaid_limit,
                    partner.risk_invoice_unpaid_include,
                    "risk_invoice_unpaid_include",
                    "risk_invoice_unpaid_limit",
                ),
                (
                    "Limite de Otros Saldos",
                    partner.risk_account_amount,
                    partner.risk_account_amount_limit,
                    partner.risk_account_amount_include,
                    "risk_account_amount_include",
                    "risk_account_amount_limit",
                ),
                (
                    "Limite de Otros Saldos Vencidos",
                    partner.risk_account_amount_unpaid,
                    partner.risk_account_amount_unpaid_limit,
                    partner.risk_account_amount_unpaid_include,
                    "risk_account_amount_unpaid_include",
                    "risk_account_amount_unpaid_limit",
                ),
            ]
            items = []
            for label, current, limit, included, include_field, limit_field in lines:
                current_value = float(current or 0.0)
                limit_value = float(limit or 0.0)
                if limit_value > 0:
                    progress = min((current_value / limit_value) * 100.0, 100.0)
                    exceeded = current_value > limit_value
                else:
                    progress = 0.0
                    exceeded = False
                items.append(
                    {
                        "label": label,
                        "current": current_value,
                        "limit": limit_value,
                        "included": bool(included),
                        "progress": progress,
                        "exceeded": exceeded,
                        "include_field": include_field,
                        "limit_field": limit_field,
                    }
                )
            partner.risk_dashboard_json = {
                "currency_symbol": currency.symbol or "",
                "currency_position": currency.position or "after",
                "can_edit": bool(partner.risk_allow_edit),
                "credit_total": float(partner.risk_total or 0.0),
                "credit_limit": float(partner.credit_limit or 0.0),
                "remaining_value": float(partner.risk_remaining_value or 0.0),
                "remaining_percentage": float(partner.risk_remaining_percentage or 0.0),
                "items": items,
            }

    def _get_amount_in_risk_currency(
        self, currency, amount_residual_currency, amount_residual, account
    ):
        self.ensure_one()
        company_currency = self.env.company.currency_id
        risk_currency = self.risk_currency_id
        line_currency = currency if currency and currency.id else False

        if line_currency and line_currency.id == risk_currency.id:
            return amount_residual_currency
        if risk_currency.id == company_currency.id:
            return amount_residual
        if line_currency:
            return line_currency._convert(
                amount_residual_currency,
                risk_currency,
                self.env.company,
                fields.Date.context_today(self),
                round=False,
            )
        return company_currency._convert(
            amount_residual,
            risk_currency,
            self.env.company,
            fields.Date.context_today(self),
            round=False,
        )

    def _prepare_risk_account_vals(self, groups):
        vals = super()._prepare_risk_account_vals(groups)
        draft_total = 0.0
        draft_lines = self.env["account.move.line"].search(
            groups["draft"]["domain"] + [("partner_id", "child_of", self.ids)]
        )
        for line in draft_lines:
            move = line.move_id
            term = move.invoice_payment_term_id
            if not term or not term._pba_is_credit_payment_term():
                continue
            draft_total += self._get_amount_in_risk_currency(
                line.currency_id,
                line.amount_residual_currency,
                line.amount_residual,
                line.account_id,
            )
        vals["risk_invoice_draft"] = draft_total
        return vals
