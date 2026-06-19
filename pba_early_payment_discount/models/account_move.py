from collections import defaultdict

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools import frozendict
from odoo.tools.float_utils import float_compare, float_is_zero


class AccountMove(models.Model):
    _inherit = "account.move"

    pba_early_payment_discount_percent = fields.Float(
        string="Descuento pronto pago (%)",
        digits="Discount",
        copy=True,
    )
    pba_early_payment_discount_days = fields.Integer(
        string="Días pronto pago",
        copy=True,
    )
    pba_show_early_payment_discount = fields.Boolean(
        compute="_compute_pba_show_early_payment_discount",
    )
    pba_can_edit_early_payment_discount = fields.Boolean(
        compute="_compute_pba_can_edit_early_payment_discount",
    )

    @api.depends("invoice_payment_term_id", "invoice_payment_term_id.early_discount")
    def _compute_pba_show_early_payment_discount(self):
        for move in self:
            move.pba_show_early_payment_discount = bool(
                move.invoice_payment_term_id.early_discount
            )

    def _pba_has_invoice_payments(self):
        self.ensure_one()
        if self.reconciled_payment_ids:
            return True
        payment_term_lines = self.line_ids.filtered(lambda line: line.display_type == "payment_term")
        return bool(payment_term_lines.matched_debit_ids | payment_term_lines.matched_credit_ids)

    def _pba_user_can_edit_early_payment_discount(self):
        return self.env.user.has_group(
            "pba_early_payment_discount.group_pba_edit_posted_early_payment_discount"
        )

    def _pba_is_manual_epd_change(self, vals):
        self.ensure_one()
        if "pba_early_payment_discount_percent" in vals and float_compare(
            vals["pba_early_payment_discount_percent"] or 0.0,
            self.pba_early_payment_discount_percent or 0.0,
            precision_digits=6,
        ) != 0:
            return True
        if "pba_early_payment_discount_days" in vals and (
            vals["pba_early_payment_discount_days"] or 0
        ) != (self.pba_early_payment_discount_days or 0):
            return True
        return False

    @api.depends(
        "state",
        "reconciled_payment_ids",
        "line_ids.matched_debit_ids",
        "line_ids.matched_credit_ids",
    )
    def _compute_pba_can_edit_early_payment_discount(self):
        can_edit = self._pba_user_can_edit_early_payment_discount()
        for move in self:
            if not can_edit:
                move.pba_can_edit_early_payment_discount = False
            elif move.state == "draft":
                move.pba_can_edit_early_payment_discount = True
            elif move.state == "posted" and not move._pba_has_invoice_payments():
                move.pba_can_edit_early_payment_discount = True
            else:
                move.pba_can_edit_early_payment_discount = False

    @api.constrains(
        "pba_early_payment_discount_percent",
        "pba_early_payment_discount_days",
        "invoice_payment_term_id",
        "state",
    )
    def _check_pba_early_payment_discount(self):
        for move in self.filtered(
            lambda m: m.is_invoice(True)
            and m.state in ("draft", "posted")
            and m.pba_can_edit_early_payment_discount
        ):
            term = move.invoice_payment_term_id
            if not term or not term.early_discount:
                if not float_is_zero(move.pba_early_payment_discount_percent, precision_digits=6):
                    raise ValidationError(
                        "El descuento por pronto pago solo aplica con un término de pago "
                        "que tenga descuento por pronto pago activado."
                    )
                continue
            if move.pba_early_payment_discount_percent < 0:
                raise ValidationError("El descuento por pronto pago no puede ser negativo.")
            if not float_is_zero(move.pba_early_payment_discount_percent, precision_digits=6):
                days = move._pba_get_effective_early_discount_days()
                if days <= 0:
                    raise ValidationError(
                        "Los días de pronto pago deben ser mayores que cero cuando hay descuento."
                    )

    def _pba_get_partner_early_payment_discount_values(self):
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id
        if self.is_sale_document(include_receipts=True):
            return partner.pba_early_payment_discount_percent, partner.pba_early_payment_discount_days
        if self.is_purchase_document(include_receipts=True):
            return (
                partner.pba_supplier_early_payment_discount_percent,
                partner.pba_supplier_early_payment_discount_days,
            )
        return 0.0, 0

    def _pba_get_effective_early_discount_percent(self):
        self.ensure_one()
        term = self.invoice_payment_term_id
        if not term or not term.early_discount:
            return 0.0
        return self.pba_early_payment_discount_percent

    def _pba_get_effective_early_discount_days(self):
        self.ensure_one()
        term = self.invoice_payment_term_id
        if not term or not term.early_discount:
            return 0
        if float_is_zero(self.pba_early_payment_discount_percent, precision_digits=6):
            return 0
        if self.pba_early_payment_discount_days > 0:
            return self.pba_early_payment_discount_days
        _partner_percent, partner_days = self._pba_get_partner_early_payment_discount_values()
        if partner_days > 0:
            return partner_days
        return term.discount_days

    def _pba_compute_epd_result_per_invoice_line(self, invoice_lines):
        self.ensure_one()
        AccountTax = self.env["account.tax"]
        company = self.company_id or self.env.company
        currency = self.currency_id or company.currency_id
        discount_percentage = self._pba_get_effective_early_discount_percent()
        discount_percentage_name = f"{discount_percentage}%"
        percentage = discount_percentage / 100
        sign = self.direction_sign

        def grouping_function(base_line, tax_data):
            return {
                "account_id": base_line["account_id"].id,
                "analytic_distribution": base_line["analytic_distribution"],
                "tax_ids": [Command.set([tax_data["tax"].id for tax_data in base_line["tax_details"]["taxes_data"]])],
            }

        def dispatch_exclude_function(base_line, tax_data):
            return not tax_data["tax"]._can_be_discounted()

        product_lines = self.invoice_line_ids.filtered(lambda line: line.display_type == "product")
        base_lines = [
            {
                **self._prepare_product_base_line_for_taxes_computation(line),
                "_invoice_line": line,
            }
            for line in product_lines
        ]
        AccountTax._add_tax_details_in_base_lines(base_lines, company)
        AccountTax._round_base_lines_tax_details(base_lines, company)
        for base_line in base_lines:
            base_line["_invoice_line"] = base_line["record"]
        base_lines = AccountTax._dispatch_taxes_into_new_base_lines(
            base_lines, company, dispatch_exclude_function
        )

        result_per_invoice_line = {}
        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(
            base_lines, grouping_function
        )
        values_per_grouping_key = AccountTax._aggregate_base_lines_aggregated_values(
            base_lines_aggregated_values
        )
        for grouping_key, values in values_per_grouping_key.items():
            if not grouping_key:
                continue
            epd_amount_currency = currency.round(sign * values["total_excluded_currency"] * percentage)
            epd_balance = company.currency_id.round(sign * values["total_excluded"] * percentage)
            grouping_key_line = frozendict({
                "move_id": self.id,
                **grouping_key,
                "display_type": "epd",
            })
            grouping_key_counterpart = frozendict({
                "move_id": self.id,
                "account_id": grouping_key["account_id"],
                "display_type": "epd",
            })
            aggregated_base_lines = [
                base_line
                for base_line, _taxes_data in values["base_line_x_taxes_data"]
            ]
            for base_line in aggregated_base_lines:
                invoice_line = base_line["_invoice_line"]
                result_per_invoice_line[invoice_line] = {
                    grouping_key_line: {
                        "name": _("Early Payment Discount (%s)", discount_percentage_name),
                        "amount_currency": 0.0,
                        "balance": 0.0,
                    },
                    grouping_key_counterpart: {
                        "name": _("Early Payment Discount (%s)", discount_percentage_name),
                        "amount_currency": 0.0,
                        "balance": 0.0,
                        "tax_ids": [Command.clear()],
                    },
                }
            target_factors = [
                {
                    "factor": base_line["tax_details"]["raw_total_excluded_currency"],
                    "base_line": base_line,
                }
                for base_line in aggregated_base_lines
            ]
            amounts_to_distribute = AccountTax._distribute_delta_amount_smoothly(
                precision_digits=currency.decimal_places,
                delta_amount=epd_amount_currency,
                target_factors=target_factors,
            )
            for target_factor, amount_to_distribute in zip(target_factors, amounts_to_distribute):
                invoice_line = target_factor["base_line"]["_invoice_line"]
                epd_needed = result_per_invoice_line[invoice_line]
                epd_needed[grouping_key_line]["amount_currency"] -= amount_to_distribute
                epd_needed[grouping_key_counterpart]["amount_currency"] += amount_to_distribute
            amounts_to_distribute = AccountTax._distribute_delta_amount_smoothly(
                precision_digits=company.currency_id.decimal_places,
                delta_amount=epd_balance,
                target_factors=target_factors,
            )
            for target_factor, amount_to_distribute in zip(target_factors, amounts_to_distribute):
                invoice_line = target_factor["base_line"]["_invoice_line"]
                epd_needed = result_per_invoice_line[invoice_line]
                epd_needed[grouping_key_line]["balance"] -= amount_to_distribute
                epd_needed[grouping_key_counterpart]["balance"] += amount_to_distribute
        return {
            line: {key: frozendict(values) for key, values in epd_needed.items()}
            for line, epd_needed in result_per_invoice_line.items()
            if line in invoice_lines
        }

    def _pba_early_payment_discount_is_disabled(self):
        self.ensure_one()
        term = self.invoice_payment_term_id
        return bool(
            term
            and term.early_discount
            and float_is_zero(self.pba_early_payment_discount_percent, precision_digits=6)
        )

    def _pba_has_custom_early_payment_discount(self):
        self.ensure_one()
        term = self.invoice_payment_term_id
        if not term or not term.early_discount:
            return False
        if self._pba_early_payment_discount_is_disabled():
            return True
        percent = self._pba_get_effective_early_discount_percent()
        days = self._pba_get_effective_early_discount_days()
        return (
            float_compare(percent, term.discount_percentage, precision_digits=6) != 0
            or days != term.discount_days
        )

    def _pba_get_payment_term_for_computation(self):
        self.ensure_one()
        term = self.invoice_payment_term_id
        if not term or not term.early_discount:
            return term
        if not self._pba_has_custom_early_payment_discount():
            return term
        if self._pba_early_payment_discount_is_disabled():
            return term.new({
                "early_discount": False,
                "discount_percentage": term.discount_percentage,
                "discount_days": term.discount_days,
                "early_pay_discount_computation": term.early_pay_discount_computation,
                "line_ids": term.line_ids,
            })
        return term.new({
            "early_discount": True,
            "discount_percentage": self._pba_get_effective_early_discount_percent(),
            "discount_days": self._pba_get_effective_early_discount_days(),
            "early_pay_discount_computation": term.early_pay_discount_computation,
            "line_ids": term.line_ids,
        })

    def _pba_get_early_payment_discount_payment_currency(self, currency):
        self.ensure_one()
        if self.currency_id == currency:
            return currency
        if (
            self.currency_id != self.company_currency_id
            and currency == self.company_currency_id
        ):
            return self.currency_id
        return currency

    def _is_eligible_for_early_payment_discount(self, currency, reference_date):
        self.ensure_one()
        if self._pba_early_payment_discount_is_disabled():
            return False
        payment_currency = self._pba_get_early_payment_discount_payment_currency(currency)
        return super()._is_eligible_for_early_payment_discount(
            payment_currency, reference_date
        )

    def _pba_get_move_for_early_payment_discount_computation(self):
        self.ensure_one()
        payment_term = self._pba_get_payment_term_for_computation()
        if payment_term == self.invoice_payment_term_id:
            return self
        return self.new({"invoice_payment_term_id": payment_term}, origin=self)

    def _pba_remap_early_payment_discount_lines_to_real_payment_term(self, result, virtual_move):
        self.ensure_one()
        if virtual_move is self:
            return result
        virtual_payment_term = virtual_move.line_ids.filtered(
            lambda line: line.display_type == "payment_term"
        )
        real_payment_term = self.line_ids.filtered(lambda line: line.display_type == "payment_term")
        if len(virtual_payment_term) != 1 or len(real_payment_term) != 1:
            return result
        remapped = {
            key: defaultdict(lambda: {})
            for key in ("term_lines", "tax_lines", "base_lines")
        }
        for key in remapped:
            line_values = result[key].get(virtual_payment_term)
            if line_values:
                remapped[key][real_payment_term] = line_values
        return remapped

    def _get_invoice_counterpart_amls_for_early_payment_discount_per_payment_term_line(self):
        move = self._pba_get_move_for_early_payment_discount_computation()
        if move._pba_early_payment_discount_is_disabled():
            return {
                "term_lines": defaultdict(lambda: {}),
                "tax_lines": defaultdict(lambda: {}),
                "base_lines": defaultdict(lambda: {}),
            }
        result = super(
            AccountMove,
            move,
        )._get_invoice_counterpart_amls_for_early_payment_discount_per_payment_term_line()
        return self._pba_remap_early_payment_discount_lines_to_real_payment_term(result, move)

    def _pba_apply_partner_early_payment_discount_defaults(self):
        for move in self.filtered(lambda m: m.is_invoice(True) and m.state == "draft"):
            term = move.invoice_payment_term_id
            if not term or not term.early_discount:
                vals = {
                    "pba_early_payment_discount_percent": 0.0,
                    "pba_early_payment_discount_days": 0,
                }
            else:
                partner_percent, partner_days = move._pba_get_partner_early_payment_discount_values()
                vals = {
                    "pba_early_payment_discount_percent": partner_percent or term.discount_percentage,
                    "pba_early_payment_discount_days": partner_days or term.discount_days,
                }
            move.with_context(pba_skip_early_payment_discount_access=True).write(vals)

    @api.onchange("partner_id", "invoice_payment_term_id")
    def _onchange_pba_early_payment_discount(self):
        self._pba_apply_partner_early_payment_discount_defaults()

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        moves.filtered(
            lambda m: m.is_invoice(True) and not m.reversed_entry_id
        )._pba_apply_partner_early_payment_discount_defaults()
        return moves

    def write(self, vals):
        epd_fields = {"pba_early_payment_discount_percent", "pba_early_payment_discount_days"}
        if epd_fields & set(vals) and not self.env.context.get("pba_skip_early_payment_discount_access"):
            invoices = self.filtered(
                lambda m: m.is_invoice(True) and m._pba_is_manual_epd_change(vals)
            )
            if invoices and not self._pba_user_can_edit_early_payment_discount():
                raise AccessError(
                    "No tiene permiso para modificar el descuento por pronto pago en facturas."
                )
            for move in invoices.filtered(lambda m: m.state == "posted"):
                if move._pba_has_invoice_payments():
                    raise UserError(
                        "No se puede modificar el descuento por pronto pago "
                        "cuando la factura tiene pagos registrados."
                    )
        res = super().write(vals)
        if {"partner_id", "invoice_payment_term_id"} & set(vals):
            self.filtered(
                lambda m: m.is_invoice(True) and m.state == "draft" and not m.reversed_entry_id
            )._pba_apply_partner_early_payment_discount_defaults()
        return res

    @api.depends(
        "invoice_payment_term_id",
        "invoice_date",
        "currency_id",
        "amount_total_in_currency_signed",
        "invoice_date_due",
        "pba_early_payment_discount_percent",
        "pba_early_payment_discount_days",
        "partner_id",
        "partner_id.pba_early_payment_discount_percent",
        "partner_id.pba_early_payment_discount_days",
        "partner_id.pba_supplier_early_payment_discount_percent",
        "partner_id.pba_supplier_early_payment_discount_days",
    )
    def _compute_needed_terms(self):
        super()._compute_needed_terms()
        custom_moves = self.filtered(
            lambda move: move.is_invoice(True)
            and move.invoice_line_ids
            and move._pba_has_custom_early_payment_discount()
        )
        if not custom_moves:
            return

        AccountTax = self.env["account.tax"]
        for invoice in custom_moves.with_context(bin_size=False):
            is_draft = invoice.id != invoice._origin.id
            invoice.needed_terms = {}
            invoice.needed_terms_dirty = True
            sign = 1 if invoice.is_inbound(include_receipts=True) else -1
            payment_term = invoice._pba_get_payment_term_for_computation()
            if is_draft:
                tax_amount_currency = 0.0
                tax_amount = tax_amount_currency
                untaxed_amount_currency = 0.0
                untaxed_amount = untaxed_amount_currency
                sign = invoice.direction_sign
                base_lines, _tax_lines = invoice._get_rounded_base_and_tax_lines(
                    round_from_tax_lines=False
                )
                AccountTax._add_accounting_data_in_base_lines_tax_details(
                    base_lines,
                    invoice.company_id,
                    include_caba_tags=invoice.always_tax_exigible,
                )
                tax_results = AccountTax._prepare_tax_lines(base_lines, invoice.company_id)
                for base_line, to_update in tax_results["base_lines_to_update"]:
                    untaxed_amount_currency += sign * to_update["amount_currency"]
                    untaxed_amount += sign * to_update["balance"]
                for tax_line_vals in tax_results["tax_lines_to_add"]:
                    tax_amount_currency += sign * tax_line_vals["amount_currency"]
                    tax_amount += sign * tax_line_vals["balance"]
            else:
                tax_amount_currency = invoice.amount_tax * sign
                tax_amount = invoice.amount_tax_signed
                untaxed_amount_currency = invoice.amount_untaxed * sign
                untaxed_amount = invoice.amount_untaxed_signed
            invoice_payment_terms = payment_term._compute_terms(
                date_ref=invoice.invoice_date or invoice.date or fields.Date.context_today(invoice),
                currency=invoice.currency_id,
                tax_amount_currency=tax_amount_currency,
                tax_amount=tax_amount,
                untaxed_amount_currency=untaxed_amount_currency,
                untaxed_amount=untaxed_amount,
                company=invoice.company_id,
                cash_rounding=invoice.invoice_cash_rounding_id,
                sign=sign,
            )
            for term_line in invoice_payment_terms["line_ids"]:
                key = frozendict({
                    "move_id": invoice.id,
                    "date_maturity": fields.Date.to_date(term_line.get("date")),
                    "discount_date": invoice_payment_terms.get("discount_date"),
                })
                values = {
                    "balance": term_line["company_amount"],
                    "amount_currency": term_line["foreign_amount"],
                    "discount_date": invoice_payment_terms.get("discount_date"),
                    "discount_balance": invoice_payment_terms.get("discount_balance") or 0.0,
                    "discount_amount_currency": invoice_payment_terms.get("discount_amount_currency") or 0.0,
                }
                if key not in invoice.needed_terms:
                    invoice.needed_terms[key] = values
                else:
                    invoice.needed_terms[key]["balance"] += values["balance"]
                    invoice.needed_terms[key]["amount_currency"] += values["amount_currency"]
