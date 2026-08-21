from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _is_excess_refund_wizard(self):
        return bool(self.env.context.get("account_payment_excess_refund"))

    @api.model
    def _get_line_batch_key(self, line):
        values = super()._get_line_batch_key(line)
        partner_type = self.env.context.get("excess_refund_partner_type")
        if partner_type:
            values = dict(values)
            values["partner_type"] = partner_type
        return values

    @api.depends("line_ids")
    def _compute_from_lines(self):
        super()._compute_from_lines()
        partner_type = self.env.context.get("excess_refund_partner_type")
        if not partner_type:
            return
        for wizard in self.filtered(lambda item: item.can_edit_wizard):
            wizard.partner_type = partner_type

    @api.depends("available_journal_ids")
    def _compute_journal_id(self):
        for wizard in self.filtered(lambda item: item._is_excess_refund_wizard()):
            configured = wizard.company_id.excess_refund_journal_id
            if (
                configured
                and configured in wizard.available_journal_ids
                and wizard.journal_id not in wizard.available_journal_ids
            ):
                wizard.journal_id = configured
        super()._compute_journal_id()

    def _convert_to_wizard_currency(self, installments):
        """Use stored residuals directly for excess refunds.

        When refunding in company currency a foreign excess line, use
        ``amount_residual`` instead of converting ``amount_residual_currency``
        again (avoids VES -> USD -> VES round-trips).
        """
        if not self._is_excess_refund_wizard():
            return super()._convert_to_wizard_currency(installments)
        self.ensure_one()
        total_amount = 0.0
        wizard_curr = self.currency_id
        comp_curr = self.company_currency_id
        payment_date = self.payment_date or fields.Date.context_today(self)
        for installment in installments:
            line = installment["line"]
            amount_residual = installment["amount_residual"]
            amount_residual_currency = installment["amount_residual_currency"]
            currency = line.currency_id
            if currency == wizard_curr:
                total_amount += amount_residual_currency
            elif wizard_curr == comp_curr:
                total_amount += amount_residual
            else:
                total_amount += comp_curr._convert(
                    amount_residual,
                    wizard_curr,
                    self.company_id,
                    payment_date,
                )
        return total_amount

    def _get_excess_refund_max_amount(self):
        self.ensure_one()
        lines = self.line_ids
        if not lines:
            return 0.0
        wizard_curr = self.currency_id
        comp_curr = self.company_currency_id
        payment_date = self.payment_date or fields.Date.context_today(self)
        if wizard_curr == comp_curr:
            return abs(sum(lines.mapped("amount_residual")))
        if all(line.currency_id == wizard_curr for line in lines):
            return abs(sum(lines.mapped("amount_residual_currency")))
        company_residual = abs(sum(lines.mapped("amount_residual")))
        return abs(
            comp_curr._convert(
                company_residual,
                wizard_curr,
                self.company_id,
                payment_date,
            )
        )

    @api.constrains("amount", "currency_id", "payment_date", "line_ids")
    def _check_excess_refund_amount(self):
        for wizard in self:
            if not wizard._is_excess_refund_wizard():
                continue
            if wizard.currency_id.compare_amounts(wizard.amount, 0.0) <= 0:
                raise UserError(_("The excess refund amount must be greater than zero."))
            max_amount = wizard._get_excess_refund_max_amount()
            if wizard.currency_id.compare_amounts(wizard.amount, max_amount) > 0:
                raise UserError(
                    _(
                        "You cannot refund more than the open excess (%(amount)s).",
                        amount=max_amount,
                    )
                )


    def _prepare_excess_refund_forced_rate(self, lines):
        self.ensure_one()
        if self.currency_id != self.company_currency_id:
            return None
        residual = abs(sum(lines.mapped("amount_residual")))
        residual_currency = abs(sum(lines.mapped("amount_residual_currency")))
        if self.company_currency_id.is_zero(residual):
            return None
        if all(line.currency_id == self.company_currency_id for line in lines):
            return None
        return residual_currency / residual

    def _reconcile_payments(self, to_process, edit_mode=False):
        if self._is_excess_refund_wizard():
            for vals in to_process:
                if "rate" in vals:
                    continue
                rate = self._prepare_excess_refund_forced_rate(vals["to_reconcile"])
                if rate is not None:
                    vals["rate"] = rate
        return super()._reconcile_payments(to_process, edit_mode=edit_mode)

    def _prepare_excess_refund_payment_vals(self, payment_vals):
        self.ensure_one()
        invoice = self.env["account.move"].browse(
            self.env.context.get("excess_refund_invoice_id")
        )
        excess_line = self.line_ids[:1]
        source_payment = (
            excess_line.payment_id
            or excess_line.move_id.origin_payment_id
            or self.env["account.payment"].browse(
                (self.env.context.get("excess_refund_source_payment_ids") or [False])[0]
            )
        )
        payment_vals.update(
            {
                "excess_refund_invoice_id": invoice.id or False,
                "excess_refund_line_id": excess_line.id or False,
                "excess_refund_source_payment_id": source_payment.id or False,
            }
        )
        if invoice and not payment_vals.get("memo"):
            payment_vals["memo"] = _(
                "Excess refund: %(invoice)s",
                invoice=invoice.display_name,
            )
        return payment_vals

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        if self._is_excess_refund_wizard():
            payment_vals = self._prepare_excess_refund_payment_vals(payment_vals)
        return payment_vals

    def _create_payment_vals_from_batch(self, batch_result):
        payment_vals = super()._create_payment_vals_from_batch(batch_result)
        if self._is_excess_refund_wizard():
            payment_vals = self._prepare_excess_refund_payment_vals(payment_vals)
        return payment_vals

    def action_create_payments(self):
        if self._is_excess_refund_wizard():
            self.payment_difference_handling = "open"
            self._check_excess_refund_amount()
        return super().action_create_payments()
