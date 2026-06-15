from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    risk_dashboard_json = fields.Json(compute="_compute_risk_dashboard_json")
    pba_block_sale_on_overdue_all = fields.Boolean(
        string="Bloquear ventas por facturas vencidas",
        help="Impide confirmar pedidos y publicar facturas de clientes con facturas vencidas, "
        "tanto al contado como a credito.",
    )
    pba_block_sale_on_overdue_credit = fields.Boolean(
        string="Bloquear ventas a credito por facturas vencidas",
        help="Impide confirmar pedidos y publicar facturas a credito cuando el cliente "
        "tiene facturas vencidas con terminos de pago a credito.",
    )

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + [
            "pba_block_sale_on_overdue_all",
            "pba_block_sale_on_overdue_credit",
        ]

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
            "pba_block_sale_on_overdue_all",
            "pba_block_sale_on_overdue_credit",
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
        "credit_currency",
        "manual_credit_currency_id",
        "manual_credit_currency_id.symbol",
        "manual_credit_currency_id.position",
        "property_account_receivable_id.currency_id",
        "property_account_receivable_id.currency_id.symbol",
        "property_account_receivable_id.currency_id.position",
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
                    "risk_sale_order",
                ),
                (
                    "Limite de Facturas Borrador",
                    partner.risk_invoice_draft,
                    partner.risk_invoice_draft_limit,
                    partner.risk_invoice_draft_include,
                    "risk_invoice_draft_include",
                    "risk_invoice_draft_limit",
                    "risk_invoice_draft",
                ),
                (
                    "Limite de Facturas Abiertas",
                    partner.risk_invoice_open,
                    partner.risk_invoice_open_limit,
                    partner.risk_invoice_open_include,
                    "risk_invoice_open_include",
                    "risk_invoice_open_limit",
                    "risk_invoice_open",
                ),
                (
                    "Limite de Facturas Vencidas",
                    partner.risk_invoice_unpaid,
                    partner.risk_invoice_unpaid_limit,
                    partner.risk_invoice_unpaid_include,
                    "risk_invoice_unpaid_include",
                    "risk_invoice_unpaid_limit",
                    "risk_invoice_unpaid",
                ),
                (
                    "Limite de Otros Saldos",
                    partner.risk_account_amount,
                    partner.risk_account_amount_limit,
                    partner.risk_account_amount_include,
                    "risk_account_amount_include",
                    "risk_account_amount_limit",
                    "risk_account_amount",
                ),
                (
                    "Limite de Otros Saldos Vencidos",
                    partner.risk_account_amount_unpaid,
                    partner.risk_account_amount_unpaid_limit,
                    partner.risk_account_amount_unpaid_include,
                    "risk_account_amount_unpaid_include",
                    "risk_account_amount_unpaid_limit",
                    "risk_account_amount_unpaid",
                ),
            ]
            items = []
            for label, current, limit, included, include_field, limit_field, risk_field in lines:
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
                        "risk_field": risk_field,
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

    def _pba_get_overdue_invoice_lines(self, credit_only=False):
        self.ensure_one()
        commercial = self.commercial_partner_id
        _model_name, domain = commercial._get_field_risk_model_domain(
            "risk_invoice_unpaid"
        )
        lines = self.env["account.move.line"].search(domain)
        if not credit_only:
            return lines
        return lines.filtered(
            lambda line: line.move_id.invoice_payment_term_id
            and line.move_id.invoice_payment_term_id._pba_is_credit_payment_term()
        )

    def _pba_get_overdue_invoices_amount(self, credit_only=False):
        self.ensure_one()
        total = 0.0
        for line in self._pba_get_overdue_invoice_lines(credit_only=credit_only):
            total += self._get_amount_in_risk_currency(
                line.currency_id,
                line.amount_residual_currency,
                line.amount_residual,
                line.account_id,
            )
        return total

    def _pba_get_overdue_block_settings(self, company):
        partner = self.commercial_partner_id
        return (
            bool(partner.pba_block_sale_on_overdue_all),
            bool(partner.pba_block_sale_on_overdue_credit),
        )

    def _pba_is_financial_risk_enabled(self):
        self.ensure_one()
        partner = self.commercial_partner_id
        if partner.pba_block_sale_on_overdue_all or partner.pba_block_sale_on_overdue_credit:
            return True
        if partner.credit_limit > 0:
            return True
        return any(
            limit > 0
            for limit in (
                partner.risk_sale_order_limit,
                partner.risk_invoice_draft_limit,
                partner.risk_invoice_open_limit,
                partner.risk_invoice_unpaid_limit,
                partner.risk_account_amount_limit,
                partner.risk_account_amount_unpaid_limit,
            )
        )

    def _pba_overdue_invoices_exception_msg(self, company, is_credit_sale):
        self.ensure_one()
        block_all, block_credit = self._pba_get_overdue_block_settings(company)
        if block_all and self._pba_get_overdue_invoices_amount(credit_only=False) > 0:
            return _(
                "El cliente tiene facturas vencidas pendientes de pago. "
                "No se permite realizar ventas.\n"
            )
        if (
            is_credit_sale
            and block_credit
            and self._pba_get_overdue_invoices_amount(credit_only=True) > 0
        ):
            return _(
                "El cliente tiene facturas vencidas pendientes de pago. "
                "No se permite realizar ventas a credito.\n"
            )
        return ""

    @api.model
    def _get_depends_compute_risk_exception(self):
        return super()._get_depends_compute_risk_exception() + [
            "pba_block_sale_on_overdue_all",
            "pba_block_sale_on_overdue_credit",
            "child_ids.pba_block_sale_on_overdue_all",
            "child_ids.pba_block_sale_on_overdue_credit",
        ]

    @api.depends(lambda x: x._get_depends_compute_risk_exception())
    def _compute_risk_exception(self):
        super()._compute_risk_exception()
        for partner in self:
            commercial = partner.commercial_partner_id
            if not commercial._pba_is_financial_risk_enabled():
                partner.risk_exception = False
                partner.risk_amount_exceeded = 0.0
                continue
            company = partner.company_id or self.env.company
            block_all, block_credit = partner._pba_get_overdue_block_settings(company)
            if block_all and partner._pba_get_overdue_invoices_amount(
                credit_only=False
            ) > 0:
                partner.risk_exception = True
            elif block_credit and partner._pba_get_overdue_invoices_amount(
                credit_only=True
            ) > 0:
                partner.risk_exception = True

    def _get_risk_sale_order_domain(self):
        domain = super()._get_risk_sale_order_domain()
        domain += [
            ("display_type", "=", False),
            ("qty_to_invoice", ">", 0),
            ("order_id.invoice_status", "!=", "invoiced"),
        ]
        return domain

    def action_open_risk_detail(self, risk_field):
        self.ensure_one()
        return self.with_context(open_risk_field=risk_field).open_risk_pivot_info()

    def open_risk_pivot_info(self):
        open_risk_field = self.env.context.get("open_risk_field")
        if open_risk_field == "risk_sale_order":
            return self._pba_action_open_risk_sale_orders()
        if open_risk_field in (
            "risk_invoice_draft",
            "risk_invoice_open",
            "risk_invoice_unpaid",
        ):
            return self._pba_action_open_risk_invoices(open_risk_field)
        if open_risk_field in ("risk_account_amount", "risk_account_amount_unpaid"):
            return self._pba_action_open_risk_move_lines(open_risk_field)
        return super().open_risk_pivot_info()

    def _pba_action_open_risk_invoices(self, risk_field):
        self.ensure_one()
        _model_name, line_domain = self._get_field_risk_model_domain(risk_field)
        lines = self.env["account.move.line"].search(line_domain)
        moves = lines.move_id
        if risk_field in ("risk_invoice_draft", "risk_invoice_unpaid"):
            moves = moves.filtered(
                lambda move: move.invoice_payment_term_id
                and move.invoice_payment_term_id._pba_is_credit_payment_term()
            )
        titles = {
            "risk_invoice_draft": _("Facturas en borrador"),
            "risk_invoice_open": _("Facturas abiertas"),
            "risk_invoice_unpaid": _("Facturas vencidas"),
        }
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account.action_move_out_invoice_type"
        )
        action.update(
            {
                "name": titles[risk_field],
                "domain": [("id", "in", moves.ids)],
                "target": "current",
                "context": {
                    "default_move_type": "out_invoice",
                    "search_default_out_invoice": 1,
                },
            }
        )
        return action

    def _pba_action_open_risk_sale_orders(self):
        self.ensure_one()
        lines = self.env["sale.order.line"].search(self._get_risk_sale_order_domain())
        orders = lines.order_id.filtered(
            lambda order: order.payment_term_id
            and order.payment_term_id._pba_is_credit_payment_term()
        )
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_orders")
        action.update(
            {
                "name": _("Pedidos de venta pendientes de facturar"),
                "domain": [("id", "in", orders.ids)],
                "target": "current",
            }
        )
        return action

    def _pba_action_open_risk_move_lines(self, risk_field):
        self.ensure_one()
        model_name, domain = self._get_field_risk_model_domain(risk_field)
        titles = {
            "risk_account_amount": _("Otros saldos abiertos"),
            "risk_account_amount_unpaid": _("Otros saldos vencidos"),
        }
        return {
            "type": "ir.actions.act_window",
            "name": titles[risk_field],
            "res_model": model_name,
            "view_mode": "list",
            "views": [(False, "list")],
            "domain": domain,
            "target": "current",
        }

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
        unpaid_total = 0.0
        unpaid_lines = self.env["account.move.line"].search(
            groups["unpaid"]["domain"] + [("partner_id", "child_of", self.ids)]
        )
        for line in unpaid_lines:
            move = line.move_id
            term = move.invoice_payment_term_id
            if not term or not term._pba_is_credit_payment_term():
                continue
            if self.property_account_receivable_id.id != line.account_id.id:
                continue
            unpaid_total += self._get_amount_in_risk_currency(
                line.currency_id,
                line.amount_residual_currency,
                line.amount_residual,
                line.account_id,
            )
        vals["risk_invoice_unpaid"] = unpaid_total
        return vals
