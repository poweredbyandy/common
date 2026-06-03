from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountMoveGoalCommissionLine(models.Model):
    _name = "account.move.goal.commission.line"
    _description = "Linea de comision por meta"
    _inherit = ["mail.thread"]
    _order = "id asc"

    invoice_id = fields.Many2one(
        comodel_name="account.move",
        required=True,
        ondelete="cascade",
        tracking=True,
    )
    payment_id = fields.Many2one(
        comodel_name="account.payment",
        tracking=True,
    )
    credit_note_move_id = fields.Many2one(
        comodel_name="account.move",
        string="Nota de credito",
        ondelete="restrict",
        tracking=True,
    )
    payment_move_id = fields.Many2one(
        comodel_name="account.move",
        required=True,
        tracking=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        required=True,
        tracking=True,
    )
    payment_amount = fields.Monetary(
        currency_field="currency_id",
        required=True,
        tracking=True,
    )
    commission_percent = fields.Float(
        required=True,
        tracking=True,
    )
    commission_amount = fields.Monetary(
        currency_field="currency_id",
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        selection=[
            ("waiting", "En espera"),
            ("invoiced", "Facturada"),
            ("paid", "Pagada"),
        ],
        default="waiting",
        required=True,
        tracking=True,
    )
    vendor_bill_id = fields.Many2one(
        comodel_name="account.move",
        domain=[("move_type", "=", "in_invoice")],
        tracking=True,
    )
    description = fields.Char(
        required=True,
        tracking=True,
    )

    @api.constrains("payment_id", "credit_note_move_id")
    def _check_source(self):
        for line in self:
            if bool(line.payment_id) == bool(line.credit_note_move_id):
                raise ValidationError(
                    _("Cada linea debe tener un pago o una nota de credito, no ambos ni ninguno.")
                )

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines.invoice_id._recompute_goal_commission_pending_stats()
        lines.invoice_id._recompute_goal_commission_collectible_for_seller_months()
        return lines

    def write(self, vals):
        if "vendor_bill_id" in vals and not vals.get("vendor_bill_id"):
            vals["state"] = "waiting"
        elif vals.get("vendor_bill_id") and "state" not in vals:
            vals["state"] = "invoiced"
        result = super().write(vals)
        self.invoice_id._recompute_goal_commission_pending_stats()
        self.invoice_id._recompute_goal_commission_collectible_for_seller_months()
        return result

    def unlink(self):
        invoices = self.invoice_id
        result = super().unlink()
        invoices._recompute_goal_commission_pending_stats()
        invoices._recompute_goal_commission_collectible_for_seller_months()
        return result


class AccountMove(models.Model):
    _inherit = "account.move"

    goal_commission_line_ids = fields.One2many(
        comodel_name="account.move.goal.commission.line",
        inverse_name="invoice_id",
        string="Comisiones por meta",
    )
    goal_commission_state = fields.Selection(
        selection=[
            ("waiting", "En espera"),
            ("invoiced", "Facturada"),
            ("paid", "Pagada"),
        ],
        string="Estado de Comision por Meta",
        compute="_compute_goal_commission_state",
        store=True,
        default="waiting",
    )
    is_goal_commission_vendor_bill = fields.Boolean(
        string="Es Factura de Comision por Meta",
        default=False,
        copy=False,
    )
    goal_commission_source_invoice_id = fields.Many2one(
        comodel_name="account.move",
        string="Factura Origen Comision por Meta",
        copy=False,
    )
    goal_commission_vendor_bill_count = fields.Integer(
        string="Comisiones Facturadas",
        compute="_compute_goal_commission_vendor_bill_count",
    )
    goal_commission_available = fields.Boolean(
        string="Disponible para comisionar por meta",
        compute="_compute_goal_commission_available",
        store=True,
        index=True,
    )
    goal_commission_collectible = fields.Boolean(
        string="Comision cobrable por meta",
        compute="_compute_goal_commission_collectible",
        store=True,
        index=True,
    )
    goal_commission_payable_date = fields.Date(
        string="Fecha cobro para comision",
        compute="_compute_goal_commission_collectible",
        store=True,
        index=True,
        help="Mes en que la factura queda cobrada y la comision puede pagarse.",
    )
    goal_commission_net_untaxed = fields.Monetary(
        string="Subtotal neto comision",
        currency_field="currency_id",
        compute="_compute_goal_commission_net_untaxed",
        store=True,
    )
    goal_commission_pending_total = fields.Monetary(
        string="Comision pendiente total",
        currency_field="currency_id",
        compute="_compute_goal_commission_pending_total",
        store=True,
    )
    goal_commission_exception = fields.Boolean(
        string="Excepcion de comision",
        copy=False,
        tracking=True,
        help="Si esta activo, la factura queda excluida de metas, reportes y pagos de comision.",
    )

    def _goal_commission_dashboard(self):
        return self.env["goal.commission.dashboard.mixin"]

    def _recompute_goal_commission_pending_stats(self):
        partners = self.filtered(lambda move: move.move_type == "out_invoice").mapped("invoice_user_id.partner_id")
        if partners:
            partners.sudo()._compute_goal_commission_stats()

    def _recompute_goal_commission_collectible_for_seller_months(self):
        Move = self.env["account.move"]
        sellers = self.filtered(
            lambda row: row.move_type == "out_invoice" and row.state == "posted"
        ).mapped("invoice_user_id")
        if not sellers:
            return
        invoices = Move.search([
            ("move_type", "=", "out_invoice"),
            ("state", "=", "posted"),
            ("invoice_user_id", "in", sellers.ids),
        ])
        if invoices:
            invoices._goal_commission_persist_stored_fields()

    def _goal_commission_stored_field_values(self):
        self.ensure_one()
        move = self
        credit_map = move._goal_commission_dashboard()._goal_commission_batch_credit_untaxed([move.id])
        credit = credit_map.get(move.id, 0.0)
        if (
            move.move_type != "out_invoice"
            or move.state != "posted"
            or move._goal_commission_is_reversed_for_commission()
        ):
            net_untaxed = 0.0
        else:
            net_untaxed = max(0.0, move.amount_untaxed - credit)
        pending_total = (
            move._goal_commission_pending_amount_live()
            if move._goal_commission_pending_eligible()
            else 0.0
        )
        collectible = move._is_goal_commission_collectible()
        payable_date = move._goal_commission_payable_date_value() if collectible else False
        available = False
        if (
            move.move_type == "out_invoice"
            and move.state == "posted"
            and not move._goal_commission_blocks_commission()
            and move._is_goal_commission_fully_collected()
            and move._is_goal_commission_active_for_invoice()
        ):
            percent = move._current_goal_percent()
            if percent > 0:
                waiting_lines = move.goal_commission_line_ids.filtered(
                    lambda line: line.state == "waiting" and not line.vendor_bill_id
                )
                if waiting_lines:
                    available = True
                elif not move.goal_commission_line_ids and pending_total > 0:
                    available = True
        return {
            "goal_commission_net_untaxed": net_untaxed,
            "goal_commission_pending_total": pending_total,
            "goal_commission_collectible": collectible,
            "goal_commission_payable_date": payable_date,
            "goal_commission_available": available,
        }

    def _goal_commission_persist_stored_fields(self):
        invoices = self.filtered(lambda move: move.move_type == "out_invoice")
        if not invoices:
            return
        field_names = [
            "goal_commission_net_untaxed",
            "goal_commission_pending_total",
            "goal_commission_collectible",
            "goal_commission_payable_date",
            "goal_commission_available",
        ]
        batch_size = 200
        for offset in range(0, len(invoices), batch_size):
            batch = invoices[offset : offset + batch_size]
            for move in batch:
                values = move._goal_commission_stored_field_values()
                self.env.cr.execute(
                    """
                    UPDATE account_move
                       SET goal_commission_net_untaxed = %s,
                           goal_commission_pending_total = %s,
                           goal_commission_collectible = %s,
                           goal_commission_payable_date = %s,
                           goal_commission_available = %s
                     WHERE id = %s
                    """,
                    (
                        values["goal_commission_net_untaxed"],
                        values["goal_commission_pending_total"],
                        values["goal_commission_collectible"],
                        values["goal_commission_payable_date"] or None,
                        values["goal_commission_available"],
                        move.id,
                    ),
                )
            batch.invalidate_recordset(field_names)

    def _goal_commission_document_date(self):
        self.ensure_one()
        return self.invoice_date or self.date

    def _goal_commission_payable_date_value(self):
        self.ensure_one()
        paid_date = self._goal_commission_effective_payment_date()
        if paid_date:
            return paid_date
        if self._is_goal_commission_fully_collected():
            return self._goal_commission_document_date()
        return False

    def _goal_commission_conversion_date_from_payment_move(self, payment_move, partial=None):
        self.ensure_one()
        if payment_move.origin_payment_id and payment_move.origin_payment_id.date:
            return payment_move.origin_payment_id.date
        if partial and partial.max_date:
            return partial.max_date
        if payment_move.date:
            return payment_move.date
        if payment_move.move_type == "out_refund":
            return payment_move.invoice_date or payment_move.date or self._goal_commission_document_date()
        return self._goal_commission_document_date()

    def _goal_commission_conversion_date_from_commission_line(self, line):
        self.ensure_one()
        if line.payment_id and line.payment_id.date:
            return line.payment_id.date
        if line.payment_move_id:
            return self._goal_commission_conversion_date_from_payment_move(line.payment_move_id)
        if line.credit_note_move_id:
            credit_note = line.credit_note_move_id
            return credit_note.invoice_date or credit_note.date or self._goal_commission_document_date()
        return self._goal_commission_payable_date_value() or self._goal_commission_document_date()

    def _get_goal_commission_seller_partner(self):
        self.ensure_one()
        return self.invoice_user_id.partner_id

    def _is_goal_commission_active_for_invoice(self):
        self.ensure_one()
        if self.move_type != "out_invoice":
            return False
        start_date = self.company_id.goal_commission_start_date
        invoice_date = self.invoice_date or self.date
        if not start_date:
            return True
        return bool(invoice_date and invoice_date >= start_date)

    @api.model
    def _goal_commission_payment_states_allowed(self):
        return ("in_payment", "paid")

    def _is_goal_commission_fully_collected(self):
        self.ensure_one()
        if self._goal_commission_is_reversed_for_commission():
            return False
        if self.payment_state not in self._goal_commission_payment_states_allowed():
            return False
        return self.currency_id.is_zero(self.amount_residual)

    def _goal_commission_posted_credit_notes(self):
        self.ensure_one()
        credits = self.reversal_move_ids.filtered(
            lambda move: move.state == "posted" and move.move_type == "out_refund"
        )
        if not credits:
            credits = self.env["account.move"].search([
                ("reversed_entry_id", "=", self.id),
                ("state", "=", "posted"),
                ("move_type", "=", "out_refund"),
            ])
        return credits

    def _goal_commission_is_reversed_for_commission(self):
        self.ensure_one()
        return self.payment_state == "reversed"

    @api.depends(
        "amount_untaxed",
        "move_type",
        "state",
        "payment_state",
        "reversal_move_ids.amount_untaxed",
        "reversal_move_ids.state",
        "reversal_move_ids.move_type",
    )
    def _compute_goal_commission_net_untaxed(self):
        out_invoices = self.filtered(lambda move: move.move_type == "out_invoice" and move.state == "posted")
        credit_map = self._goal_commission_dashboard()._goal_commission_batch_credit_untaxed(out_invoices.ids)
        for move in self:
            if move.move_type != "out_invoice" or move.state != "posted" or move._goal_commission_is_reversed_for_commission():
                move.goal_commission_net_untaxed = 0.0
            else:
                credit = credit_map.get(move.id, 0.0)
                move.goal_commission_net_untaxed = max(0.0, move.amount_untaxed - credit)

    def _goal_commission_effective_untaxed_amount(self):
        self.ensure_one()
        if self.move_type != "out_invoice" or self._goal_commission_is_reversed_for_commission():
            return 0.0
        return self.goal_commission_net_untaxed

    def _goal_commission_net_amount_total(self):
        self.ensure_one()
        if self.move_type != "out_invoice" or self._goal_commission_is_reversed_for_commission():
            return 0.0
        credit_reduction = sum(
            abs(credit.amount_total) for credit in self._goal_commission_posted_credit_notes()
        )
        return max(0.0, abs(self.amount_total) - credit_reduction)

    def _goal_commission_blocks_commission(self):
        self.ensure_one()
        return (
            self.move_type != "out_invoice"
            or self.goal_commission_exception
            or self._goal_commission_is_reversed_for_commission()
            or self.currency_id.is_zero(self._goal_commission_effective_untaxed_amount())
        )

    @api.model
    def _goal_commission_report_lang(self):
        lang_model = self.env["res.lang"].sudo()
        if lang_model.search([("code", "=", "es_VE"), ("active", "=", True)], limit=1):
            return "es_VE"
        for code in ("es_419", "es_ES", "es"):
            if lang_model.search([("code", "=", code), ("active", "=", True)], limit=1):
                return code
        return self.env.user.lang or "es_ES"

    def _goal_commission_report_payment_state_es(self, payment_state):
        labels = {
            "not_paid": "Sin pagar",
            "in_payment": "En pago",
            "paid": "Pagado",
            "partial": "Pagado parcial",
            "reversed": "Revertido",
            "blocked": "Bloqueado",
        }
        return labels.get(payment_state, payment_state or "")

    def _format_goal_commission_report_date_es(self, value):
        if not value:
            return ""
        if isinstance(value, str):
            value = fields.Date.from_string(value)
        return value.strftime("%d/%m/%Y")

    def _get_goal_commission_invoice_period(self):
        self.ensure_one()
        invoice_date = self.invoice_date or self.date
        return self.env["goal.commission.period"]._get_period_for_date(invoice_date, self.company_id)

    def _current_goal_invoiced_amount(self):
        self.ensure_one()
        seller_partner = self._get_goal_commission_seller_partner()
        if not seller_partner:
            return 0.0
        period = self._get_goal_commission_invoice_period()
        if not period:
            return 0.0
        return seller_partner._get_goal_invoiced_amount_for_period(period)

    def _current_goal_percent(self):
        self.ensure_one()
        seller_partner = self._get_goal_commission_seller_partner()
        if not seller_partner:
            return 0.0
        return seller_partner._get_goal_commission_percent_for_amount(self._current_goal_invoiced_amount())

    def _current_goal_tier(self):
        self.ensure_one()
        seller_partner = self._get_goal_commission_seller_partner()
        if not seller_partner:
            return self.env["goal.commission.tier"]
        return seller_partner._get_goal_commission_tier_for_amount(self._current_goal_invoiced_amount())

    def _goal_commission_untaxed_ratio(self):
        self.ensure_one()
        net_total = self._goal_commission_net_amount_total()
        if not net_total:
            return 0.0
        ratio = self._goal_commission_effective_untaxed_amount() / net_total
        return min(max(ratio, 0.0), 1.0)

    def _goal_commission_untaxed_base_from_payment(self, paid_amount):
        self.ensure_one()
        return paid_amount * self._goal_commission_untaxed_ratio()

    def _goal_commission_paid_untaxed_amount(self):
        self.ensure_one()
        net_untaxed = self._goal_commission_effective_untaxed_amount()
        net_total = self._goal_commission_net_amount_total()
        if not net_untaxed or not net_total:
            return 0.0
        collected_total = net_total - abs(self.amount_residual)
        paid_ratio = collected_total / net_total
        paid_ratio = min(max(paid_ratio, 0.0), 1.0)
        return net_untaxed * paid_ratio

    def _goal_commission_effective_payment_date(self):
        self.ensure_one()
        receivable_lines = self.line_ids.filtered(lambda line: line.account_id.account_type == "asset_receivable")
        partials = receivable_lines.matched_debit_ids + receivable_lines.matched_credit_ids
        payment_partials = partials.filtered(
            lambda partial: (
                partial.debit_move_id.move_id.origin_payment_id
                or partial.credit_move_id.move_id.origin_payment_id
                or partial.debit_move_id.move_id.move_type == "out_refund"
                or partial.credit_move_id.move_id.move_type == "out_refund"
            )
        )
        dates = [date for date in payment_partials.mapped("max_date") if date]
        return max(dates) if dates else False

    def _goal_commission_target_currency(self):
        self.ensure_one()
        seller_partner = self._get_goal_commission_seller_partner()
        return seller_partner.goal_commission_currency_id or self.currency_id

    def _goal_commission_subtotal_field_name(self, currency):
        if not currency:
            return None
        field_name = "x_subtotal_currency_%s" % currency.id
        if field_name in self._fields:
            return field_name
        return None

    def _goal_commission_gross_subtotal_in_currency(self, currency):
        self.ensure_one()
        if not currency:
            return 0.0
        if self.currency_id == currency:
            return self.amount_untaxed or 0.0
        field_name = self._goal_commission_subtotal_field_name(currency)
        if field_name:
            return getattr(self, field_name) or 0.0
        return 0.0

    def _goal_commission_net_subtotal_in_currency(self, currency):
        self.ensure_one()
        if self.move_type != "out_invoice" or self._goal_commission_is_reversed_for_commission():
            return 0.0
        gross = self._goal_commission_gross_subtotal_in_currency(currency)
        credit_total = sum(
            credit._goal_commission_gross_subtotal_in_currency(currency)
            for credit in self._goal_commission_posted_credit_notes()
        )
        return max(0.0, gross - abs(credit_total))

    def _goal_commission_collected_subtotal_in_currency(self, currency):
        self.ensure_one()
        net_subtotal = self._goal_commission_net_subtotal_in_currency(currency)
        if self.currency_id.is_zero(self.amount_residual):
            return currency.round(net_subtotal)
        net_untaxed = self._goal_commission_effective_untaxed_amount()
        if not net_untaxed:
            return 0.0
        paid_untaxed = self._goal_commission_paid_untaxed_amount()
        return currency.round(net_subtotal * paid_untaxed / net_untaxed)

    def _goal_commission_convert_amount(self, amount, source_currency, conversion_date=None):
        self.ensure_one()
        target_currency = self._goal_commission_target_currency()
        source_currency = source_currency or self.currency_id
        if not amount:
            return target_currency.round(0.0)
        if source_currency == target_currency:
            return target_currency.round(amount)
        net_untaxed = self._goal_commission_effective_untaxed_amount()
        net_goal = self._goal_commission_net_subtotal_in_currency(target_currency)
        if source_currency == self.currency_id and net_untaxed:
            return target_currency.round(net_goal * amount / net_untaxed)
        conversion_date = conversion_date or self._goal_commission_document_date()
        return source_currency._convert(
            amount,
            target_currency,
            self.company_id,
            conversion_date,
        )

    def _goal_commission_convert_for_preview(self, amount, source_currency, conversion_date=None):
        return self._goal_commission_convert_amount(amount, source_currency, conversion_date)

    def _has_billed_goal_commission_lines(self):
        self.ensure_one()
        return bool(
            self.goal_commission_line_ids.filtered(
                lambda line: line.vendor_bill_id or line.state in ("invoiced", "paid")
            )
        )

    def _prepare_goal_commission_payment_lines_data(self):
        self.ensure_one()
        payment_lines_data = []
        commission_percent = self._current_goal_percent()
        if (
            self.move_type != "out_invoice"
            or self.state != "posted"
            or self._goal_commission_blocks_commission()
            or not self._is_goal_commission_fully_collected()
            or commission_percent <= 0
            or not self._is_goal_commission_active_for_invoice()
        ):
            return payment_lines_data
        receivable_lines = self.line_ids.filtered(lambda line: line.account_id.account_type == "asset_receivable")
        partials = receivable_lines.matched_debit_ids + receivable_lines.matched_credit_ids
        seller_partner = self._get_goal_commission_seller_partner()
        excluded_journals = seller_partner.goal_commission_excluded_journal_ids
        for partial in partials:
            if partial.debit_move_id.move_id == self:
                counterpart_line = partial.credit_move_id
                amount_currency = abs(partial.credit_amount_currency)
                currency = partial.credit_currency_id
            else:
                counterpart_line = partial.debit_move_id
                amount_currency = abs(partial.debit_amount_currency)
                currency = partial.debit_currency_id
            payment_move = counterpart_line.move_id
            if payment_move.origin_payment_id:
                if not self._is_goal_commission_fully_collected():
                    continue
                if payment_move.journal_id in excluded_journals:
                    continue
                conversion_date = self._goal_commission_conversion_date_from_payment_move(
                    payment_move,
                    partial=partial,
                )
                payment_lines_data.append(
                    {
                        "payment_id": payment_move.origin_payment_id.id,
                        "credit_note_move_id": False,
                        "payment_move_id": payment_move.id,
                        "currency_id": currency.id,
                        "conversion_date": conversion_date,
                        "payment_amount": currency.round(self._goal_commission_untaxed_base_from_payment(amount_currency)),
                        "commission_percent": commission_percent,
                        "commission_amount": currency.round(
                            self._goal_commission_untaxed_base_from_payment(amount_currency) * commission_percent / 100.0
                        ),
                        "state": "waiting",
                        "description": _(
                            "Comision por meta %(percent)s%% sobre subtotal pagado %(base)s %(currency)s de factura %(invoice)s",
                            percent=commission_percent,
                            base=currency.round(self._goal_commission_untaxed_base_from_payment(amount_currency)),
                            currency=currency.name,
                            invoice=self.name or self.ref or self.id,
                        ),
                    }
                )
            elif payment_move.move_type == "out_refund" and payment_move.reversed_entry_id == self:
                neg_base = -amount_currency
                conversion_date = self._goal_commission_conversion_date_from_payment_move(
                    payment_move,
                    partial=partial,
                )
                payment_lines_data.append(
                    {
                        "payment_id": False,
                        "credit_note_move_id": payment_move.id,
                        "payment_move_id": payment_move.id,
                        "currency_id": currency.id,
                        "conversion_date": conversion_date,
                        "payment_amount": currency.round(self._goal_commission_untaxed_base_from_payment(neg_base)),
                        "commission_percent": commission_percent,
                        "commission_amount": currency.round(
                            self._goal_commission_untaxed_base_from_payment(neg_base) * commission_percent / 100.0
                        ),
                        "state": "waiting",
                        "description": _(
                            "Ajuste por nota de credito %(nc)s sobre factura %(invoice)s",
                            nc=payment_move.name or payment_move.ref or payment_move.id,
                            invoice=self.name or self.ref or self.id,
                        ),
                    }
                )
        if payment_lines_data:
            max_commission = self.currency_id.round(
                self._goal_commission_effective_untaxed_amount() * commission_percent / 100.0
            )
            total_commission = sum(line["commission_amount"] for line in payment_lines_data)
            if total_commission > max_commission and not self.currency_id.is_zero(total_commission):
                factor = max_commission / total_commission
                for line in payment_lines_data:
                    line_currency = self.env["res.currency"].browse(line["currency_id"])
                    line["commission_amount"] = line_currency.round(line["commission_amount"] * factor)
                    line["payment_amount"] = line_currency.round(line["payment_amount"] * factor)
        return payment_lines_data

    def _goal_commission_pending_eligible(self):
        self.ensure_one()
        return (
            self.move_type == "out_invoice"
            and self.state == "posted"
            and not self._goal_commission_blocks_commission()
            and self._is_goal_commission_fully_collected()
            and self._is_goal_commission_active_for_invoice()
            and self._current_goal_percent() > 0
        )

    @api.depends(
        "move_type",
        "state",
        "goal_commission_exception",
        "payment_state",
        "amount_residual",
        "amount_untaxed",
        "amount_total",
        "goal_commission_line_ids.commission_amount",
        "goal_commission_line_ids.state",
        "goal_commission_line_ids.vendor_bill_id",
        "line_ids.matched_debit_ids.max_date",
        "line_ids.matched_credit_ids.max_date",
        "invoice_date",
        "date",
        "company_id.goal_commission_start_date",
        "invoice_user_id.partner_id.goal_commission_tier_ids.commission_percent",
        "reversal_move_ids.state",
        "reversal_move_ids.amount_untaxed",
        "reversal_move_ids.amount_total",
    )
    def _compute_goal_commission_pending_total(self):
        eligible = self.filtered(lambda move: move._goal_commission_pending_eligible())
        (self - eligible).goal_commission_pending_total = 0.0
        for move in eligible:
            move.goal_commission_pending_total = move._goal_commission_pending_amount_live()

    def _goal_commission_pending_amount_live(self):
        self.ensure_one()
        waiting_lines = self.goal_commission_line_ids.filtered(
            lambda line: line.state == "waiting" and not line.vendor_bill_id
        )
        if waiting_lines:
            return sum(waiting_lines.mapped("commission_amount"))
        if self.goal_commission_line_ids:
            return 0.0
        prepared = self._prepare_goal_commission_payment_lines_data()
        return sum(line["commission_amount"] for line in prepared)

    def _goal_commission_pending_amount(self):
        self.ensure_one()
        if self._fields.get("goal_commission_pending_total") and self.id:
            return self.goal_commission_pending_total
        return self._goal_commission_pending_amount_live()

    @api.depends("goal_commission_line_ids.state", "goal_commission_line_ids.vendor_bill_id.payment_state", "move_type")
    def _compute_goal_commission_state(self):
        for move in self:
            effective_states = []
            for line in move.goal_commission_line_ids:
                if line.vendor_bill_id:
                    effective_states.append("paid" if line.vendor_bill_id.payment_state == "paid" else "invoiced")
                else:
                    effective_states.append(line.state)
            if move.move_type != "out_invoice" or not move.goal_commission_line_ids:
                move.goal_commission_state = "waiting"
            elif all(state == "paid" for state in effective_states):
                move.goal_commission_state = "paid"
            elif any(state in ("invoiced", "paid") for state in effective_states):
                move.goal_commission_state = "invoiced"
            else:
                move.goal_commission_state = "waiting"

    @api.depends(
        "move_type",
        "state",
        "goal_commission_exception",
        "payment_state",
        "invoice_user_id",
        "goal_commission_line_ids.state",
        "goal_commission_line_ids.vendor_bill_id",
        "goal_commission_line_ids.commission_amount",
        "payment_state",
        "amount_residual",
        "amount_total",
        "amount_untaxed",
        "line_ids.matched_debit_ids",
        "line_ids.matched_credit_ids",
        "invoice_date",
        "date",
        "company_id.goal_commission_start_date",
        "invoice_user_id.partner_id.goal_commission_currency_id",
        "invoice_user_id.partner_id.goal_commission_tier_ids",
        "invoice_user_id.partner_id.goal_commission_tier_ids.min_amount",
        "invoice_user_id.partner_id.goal_commission_tier_ids.max_amount",
        "invoice_user_id.partner_id.goal_commission_tier_ids.commission_percent",
        "reversal_move_ids.state",
        "reversal_move_ids.amount_untaxed",
        "reversal_move_ids.amount_total",
    )
    def _compute_goal_commission_available(self):
        for move in self:
            available = False
            if (
                move.move_type == "out_invoice"
                and move.state == "posted"
                and not move._goal_commission_blocks_commission()
                and move._is_goal_commission_fully_collected()
                and move._is_goal_commission_active_for_invoice()
            ):
                percent = move._current_goal_percent()
                if percent > 0:
                    waiting_lines = move.goal_commission_line_ids.filtered(
                        lambda line: line.state == "waiting" and not line.vendor_bill_id
                    )
                    if waiting_lines:
                        available = True
                    elif not move.goal_commission_line_ids and move.goal_commission_pending_total > 0:
                        available = True
            move.goal_commission_available = available

    @api.depends(
        "move_type",
        "state",
        "goal_commission_exception",
        "payment_state",
        "invoice_user_id",
        "goal_commission_line_ids.state",
        "goal_commission_line_ids.vendor_bill_id",
        "goal_commission_line_ids.commission_amount",
        "amount_residual",
        "amount_total",
        "amount_untaxed",
        "line_ids.matched_debit_ids",
        "line_ids.matched_credit_ids",
        "invoice_date",
        "date",
        "company_id.goal_commission_start_date",
        "invoice_user_id.partner_id.goal_commission_currency_id",
        "invoice_user_id.partner_id.goal_commission_tier_ids",
        "invoice_user_id.partner_id.goal_commission_tier_ids.min_amount",
        "invoice_user_id.partner_id.goal_commission_tier_ids.max_amount",
        "invoice_user_id.partner_id.goal_commission_tier_ids.commission_percent",
        "reversal_move_ids.state",
        "reversal_move_ids.amount_untaxed",
        "reversal_move_ids.amount_total",
        "line_ids.matched_debit_ids.max_date",
        "line_ids.matched_credit_ids.max_date",
    )
    def _compute_goal_commission_collectible(self):
        for move in self:
            collectible = move._is_goal_commission_collectible()
            move.goal_commission_collectible = collectible
            move.goal_commission_payable_date = (
                move._goal_commission_payable_date_value() if collectible else False
            )

    def _is_goal_commission_collectible(self):
        self.ensure_one()
        if not self._goal_commission_pending_eligible():
            return False
        pending = self._goal_commission_pending_amount_live()
        return not self.currency_id.is_zero(pending)

    @api.depends("goal_commission_line_ids.vendor_bill_id", "move_type")
    def _compute_goal_commission_vendor_bill_count(self):
        for move in self:
            move.goal_commission_vendor_bill_count = (
                len(move.goal_commission_line_ids.mapped("vendor_bill_id"))
                if move.move_type == "out_invoice"
                else 0
            )

    def action_refresh_goal_commission_lines(self):
        for move in self:
            if move.move_type != "out_invoice":
                continue
            if move._has_billed_goal_commission_lines():
                raise UserError(
                    _("La factura ya tiene comisiones por meta facturadas y no puede recalcularse.")
                )
            if move.state != "posted":
                raise UserError(_("Solo se puede actualizar en facturas confirmadas."))
            if not move._is_goal_commission_active_for_invoice():
                raise UserError(_("La factura esta fuera de la fecha de inicio de comisiones configurada."))
            if move._goal_commission_is_reversed_for_commission():
                raise UserError(_("La factura revertida no genera comision por meta."))
            if move.currency_id.is_zero(move._goal_commission_effective_untaxed_amount()):
                raise UserError(
                    _("La factura no tiene base de venta neta para comision (nota de credito total o revertida).")
                )
            if not move._is_goal_commission_fully_collected():
                raise UserError(
                    _("La factura debe estar totalmente cobrada (sin saldo pendiente) para generar comision.")
                )
            if move._current_goal_percent() <= 0:
                move.goal_commission_line_ids.unlink()
                raise UserError(_("Debe existir un porcentaje de comision mayor a 0."))
            payment_lines_data = move._prepare_goal_commission_payment_lines_data()
            move.goal_commission_line_ids.unlink()
            move.goal_commission_line_ids = [fields.Command.create(vals) for vals in payment_lines_data]
        self._recompute_goal_commission_pending_stats()

    def _prepare_goal_commission_preview_line(self, invoice, line=None, prepared=None):
        invoice_label = invoice.name or invoice.ref or str(invoice.id)
        if line:
            conversion_date = invoice._goal_commission_conversion_date_from_commission_line(line)
            payment_amount = invoice._goal_commission_convert_for_preview(
                line.payment_amount,
                line.currency_id,
                conversion_date=conversion_date,
            )
            commission_amount = invoice._goal_commission_convert_for_preview(
                line.commission_amount,
                line.currency_id,
                conversion_date=conversion_date,
            )
            return {
                "description": line.description,
                "payment_amount": payment_amount,
                "commission_amount": commission_amount,
                "currency": invoice._goal_commission_target_currency().name,
            }
        if prepared:
            source_currency = self.env["res.currency"].browse(prepared["currency_id"])
            conversion_date = prepared.get("conversion_date") or invoice._goal_commission_document_date()
            payment_amount = invoice._goal_commission_convert_for_preview(
                prepared["payment_amount"],
                source_currency,
                conversion_date=conversion_date,
            )
            commission_amount = invoice._goal_commission_convert_for_preview(
                prepared["commission_amount"],
                source_currency,
                conversion_date=conversion_date,
            )
            return {
                "description": prepared["description"],
                "payment_amount": payment_amount,
                "commission_amount": commission_amount,
                "currency": invoice._goal_commission_target_currency().name,
            }
        return {
            "description": invoice_label,
            "payment_amount": 0.0,
            "commission_amount": 0.0,
            "currency": invoice._goal_commission_target_currency().name,
        }

    def prepare_goal_commission_preview_data(self):
        self.ensure_one()
        percent = self._current_goal_percent()
        target_currency = self._goal_commission_target_currency()
        lines = self.goal_commission_line_ids.filtered(lambda line: line.state == "waiting" and not line.vendor_bill_id)
        if lines:
            line_data = [self._prepare_goal_commission_preview_line(self, line=line) for line in lines]
            amount = sum(item["commission_amount"] for item in line_data)
            currency = target_currency.name
        else:
            prepared = self._prepare_goal_commission_payment_lines_data()
            if prepared:
                line_data = [self._prepare_goal_commission_preview_line(self, prepared=item) for item in prepared]
                amount = sum(item["commission_amount"] for item in line_data)
            else:
                estimated_base = self._goal_commission_collected_subtotal_in_currency(target_currency)
                estimated_amount = target_currency.round(estimated_base * percent / 100.0)
                if (
                    estimated_base > 0
                    and percent > 0
                    and self._is_goal_commission_fully_collected()
                ):
                    line_data = [{
                        "description": _(
                            "Comision estimada por cobro acumulado sobre subtotal %(base)s %(currency)s",
                            base=target_currency.round(estimated_base),
                            currency=target_currency.name,
                        ),
                        "payment_amount": target_currency.round(estimated_base),
                        "commission_amount": estimated_amount,
                        "currency": target_currency.name,
                    }]
                else:
                    line_data = []
                amount = estimated_amount if line_data else 0.0
            currency = target_currency.name
        sale_amount = target_currency.round(
            self._goal_commission_net_subtotal_in_currency(target_currency)
        )
        return {
            "name": self.name or self.ref or str(self.id),
            "date": self._format_goal_commission_report_date_es(self.invoice_date),
            "partner": self.partner_id.with_context(lang=self.env["account.move"]._goal_commission_report_lang()).display_name,
            "sale_amount": sale_amount,
            "sale_currency": target_currency.name,
            "percent": percent,
            "amount": amount,
            "currency": currency,
            "payment_state": self._goal_commission_report_payment_state_es(self.payment_state),
            "lines": line_data,
        }

    def action_open_goal_commission_billing_wizard(self):
        invoices = self.filtered(lambda move: move.move_type == "out_invoice" and move.goal_commission_collectible)
        if not invoices:
            raise UserError(_("No hay facturas cobrables seleccionadas para comisionar."))
        seller_partner = invoices.invoice_user_id.partner_id[:1]
        return {
            "name": _("Facturar Comisiones"),
            "type": "ir.actions.act_window",
            "res_model": "goal.commission.billing.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_invoice_ids": invoices.ids,
                "default_partner_id": seller_partner.id if seller_partner else False,
            },
        }

    def action_create_goal_commission_vendor_bills(self, mode="standard", selected_currency=False):
        bills = self.env["account.move"]
        grouped_payload = {}
        selected_currency_id = selected_currency.id if selected_currency else self.env.context.get("selected_currency_id")
        target_currency = self.env["res.currency"].browse(selected_currency_id) if selected_currency_id else False
        for move in self:
            if move.move_type != "out_invoice":
                continue
            if move.goal_commission_line_ids and all(
                line.state in ("invoiced", "paid") for line in move.goal_commission_line_ids
            ):
                raise UserError(
                    _("La factura %(invoice)s ya tiene su comision facturada.", invoice=move.name or move.ref or move.id)
                )
            if move.state != "posted":
                continue
            if not move._is_goal_commission_active_for_invoice():
                continue
            seller_partner = move.invoice_user_id.partner_id
            if not seller_partner:
                raise UserError(_("El vendedor no tiene partner configurado."))
            pending_lines = move.goal_commission_line_ids.filtered(lambda line: line.state == "waiting")
            if not pending_lines:
                move.action_refresh_goal_commission_lines()
                pending_lines = move.goal_commission_line_ids.filtered(lambda line: line.state == "waiting")
            if not pending_lines:
                continue
            product = seller_partner.goal_commission_product_id
            if not product:
                raise UserError(_("Debe configurar el producto de comision por meta en el contacto del vendedor."))
            for line in pending_lines:
                if mode == "only_single_currency" and target_currency and line.currency_id != target_currency:
                    continue
                if mode == "convert_to_single":
                    if not target_currency:
                        raise UserError(_("Debe definir una moneda objetivo para convertir comisiones."))
                    conversion_date = move._goal_commission_conversion_date_from_commission_line(line)
                    line_amount = line.currency_id._convert(
                        line.commission_amount,
                        target_currency,
                        move.company_id,
                        conversion_date,
                    )
                    group_currency = target_currency
                else:
                    line_amount = line.commission_amount
                    group_currency = line.currency_id
                key = (seller_partner.id, group_currency.id)
                if key not in grouped_payload:
                    grouped_payload[key] = {
                        "partner": seller_partner,
                        "currency": group_currency,
                        "product": product,
                        "line_items": [],
                        "source_invoices": self.env["account.move"],
                    }
                grouped_payload[key]["line_items"].append(
                    {
                        "commission_line": line,
                        "amount": group_currency.round(line_amount),
                        "label": "%s - %s" % (line.invoice_id.name or line.invoice_id.ref or line.invoice_id.id, line.description),
                    }
                )
                grouped_payload[key]["source_invoices"] |= line.invoice_id
        for payload in grouped_payload.values():
            bill_lines = []
            line_group = self.env["account.move.goal.commission.line"]
            source_invoices = payload["source_invoices"]
            source_labels = ", ".join(source_invoices.mapped(lambda inv: inv.name or inv.ref or str(inv.id)))
            for item in payload["line_items"]:
                line = item["commission_line"]
                line_group |= line
                bill_lines.append(
                    fields.Command.create(
                        {
                            "product_id": payload["product"].id,
                            "name": item["label"],
                            "quantity": 1.0,
                            "price_unit": item["amount"],
                        }
                    )
                )
            company = source_invoices[:1].company_id if source_invoices else self.env.company
            bill_vals = {
                "move_type": "in_invoice",
                "partner_id": payload["partner"].id,
                "currency_id": payload["currency"].id,
                "invoice_line_ids": bill_lines,
                "ref": _("Comisiones por meta de facturas: %(invoices)s", invoices=source_labels),
                "is_goal_commission_vendor_bill": True,
                "goal_commission_source_invoice_id": source_invoices[:1].id if source_invoices else False,
            }
            if payload["partner"].goal_commission_journal_id:
                bill_vals["journal_id"] = payload["partner"].goal_commission_journal_id.id
            bill = self.env["account.move"].create(bill_vals)
            bills |= bill
            line_group.write({"vendor_bill_id": bill.id, "state": "invoiced"})
        if not bills:
            raise UserError(_("No hay lineas de comision pendientes para facturar."))
        self._recompute_goal_commission_pending_stats()
        return {
            "name": _("Facturas de proveedor de comision"),
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("id", "in", bills.ids)],
        }

    def action_open_goal_commission_vendor_bills(self):
        self.ensure_one()
        bill_ids = self.env["account.move.goal.commission.line"].search(
            [("invoice_id", "=", self.id), ("vendor_bill_id", "!=", False)]
        ).mapped("vendor_bill_id")
        return {
            "name": _("Facturas de proveedor de comision"),
            "type": "ir.actions.act_window",
            "res_model": "account.move",
            "view_mode": "list,form",
            "domain": [("id", "in", bill_ids.ids)],
            "context": {"default_move_type": "in_invoice"},
        }

    def get_goal_commission_payment_voucher_data(self):
        self.ensure_one()
        commission_lines = self.env["account.move.goal.commission.line"].search(
            [("vendor_bill_id", "=", self.id)], order="invoice_id, id"
        )
        invoices_data = []
        for invoice in commission_lines.mapped("invoice_id"):
            inv_lines = commission_lines.filtered(lambda line: line.invoice_id == invoice)
            invoices_data.append(
                {
                    "invoice": invoice,
                    "name": invoice.name or invoice.ref or str(invoice.id),
                    "partner": invoice.partner_id.with_context(lang=invoice.env["account.move"]._goal_commission_report_lang()).display_name,
                    "date": invoice._format_goal_commission_report_date_es(invoice.invoice_date),
                    "percent": invoice._current_goal_percent(),
                    "lines": [
                        {
                            "description": line.description,
                            "payment_amount": line.payment_amount,
                            "commission_amount": line.commission_amount,
                            "currency": line.currency_id.name,
                        }
                        for line in inv_lines
                    ],
                    "subtotal": sum(inv_lines.mapped("commission_amount")),
                    "currency": inv_lines[:1].currency_id.name if len(inv_lines.currency_id) == 1 else self.currency_id.name,
                }
            )
        return {
            "vendor_bill": self,
            "vendor_name": self.name or self.ref or str(self.id),
            "vendor_date": self._format_goal_commission_report_date_es(self.invoice_date),
            "seller": self.partner_id.with_context(lang=self.env["account.move"]._goal_commission_report_lang()).display_name,
            "amount_total": self.amount_untaxed,
            "currency": self.currency_id.name,
            "payment_state": self._goal_commission_report_payment_state_es(self.payment_state),
            "invoices_data": invoices_data,
        }

    def action_print_goal_commission_payment_voucher(self):
        bills = self.filtered(lambda move: move.is_goal_commission_vendor_bill)
        if not bills:
            raise UserError(_("Solo se puede imprimir el comprobante en facturas de proveedor de comision por meta."))
        return self.env.ref("pba_goal_commision.action_report_goal_commission_payment_voucher").report_action(bills)

    def write(self, vals):
        result = super().write(vals)
        if {"state", "invoice_date", "payment_state", "invoice_user_id", "amount_untaxed", "amount_total", "amount_residual"} & set(vals):
            out_invoices = self.filtered(lambda move: move.move_type == "out_invoice" and move.state == "posted")
            credit_sources = self.filtered(
                lambda move: move.move_type == "out_refund" and move.reversed_entry_id and move.state == "posted"
            ).mapped("reversed_entry_id")
            out_invoices |= credit_sources
            if out_invoices:
                self.env["goal.commission.period"].sync_from_invoices(out_invoices.mapped("company_id"))
                out_invoices._recompute_goal_commission_collectible_for_seller_months()
        if "payment_state" in vals:
            vendor_bills = self.filtered(lambda move: move.move_type == "in_invoice")
            if vendor_bills:
                commission_lines = self.env["account.move.goal.commission.line"].search(
                    [("vendor_bill_id", "in", vendor_bills.ids)]
                )
                for line in commission_lines:
                    expected = "paid" if line.vendor_bill_id.payment_state == "paid" else "invoiced"
                    if line.state != expected:
                        line.state = expected
        if {"payment_state", "state", "invoice_user_id", "goal_commission_exception"} & set(vals):
            self._recompute_goal_commission_pending_stats()
        if "goal_commission_exception" in vals:
            out_invoices = self.filtered(lambda move: move.move_type == "out_invoice" and move.state == "posted")
            if out_invoices:
                out_invoices._recompute_goal_commission_collectible_for_seller_months()
        return result

    def unlink(self):
        commission_bills = self.filtered(lambda move: move.move_type == "in_invoice" and move.is_goal_commission_vendor_bill)
        if commission_bills:
            commission_lines = self.env["account.move.goal.commission.line"].sudo().search(
                [("vendor_bill_id", "in", commission_bills.ids)]
            )
            if commission_lines:
                commission_lines.write({"vendor_bill_id": False, "state": "waiting"})
        return super().unlink()

    @api.model
    def action_goal_customer_commissions_menu(self):
        self.env["goal.commission.period"].sync_from_invoices()
        xmlid = (
            "pba_goal_commision.action_customer_goal_commissions_admin"
            if self.env.user.has_group("pba_goal_commision.group_goal_commission_admin")
            else "pba_goal_commision.action_customer_goal_commissions"
        )
        action = self.env["ir.actions.actions"]._for_xml_id(xmlid)
        period = self.env["goal.commission.period"]._get_default_period()
        return self.env["goal.commission.period"].action_with_period_for_invoice_list(action, period)

    @api.model
    def action_goal_vendor_commissions_menu(self):
        xmlid = (
            "pba_goal_commision.action_vendor_goal_commissions_admin"
            if self.env.user.has_group("pba_goal_commision.group_goal_commission_admin")
            else "pba_goal_commision.action_vendor_goal_commissions"
        )
        return self.env["ir.actions.actions"]._for_xml_id(xmlid)
