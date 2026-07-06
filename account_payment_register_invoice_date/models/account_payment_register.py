from datetime import date

from odoo import Command, fields, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _get_invoice_date_sort_key(self, move):
        invoice_date = move.invoice_date or move.date or date.min
        return (invoice_date, move.id)

    def _should_reconcile_by_invoice_date(self, lines):
        self.ensure_one()
        if not self.group_payment:
            return False
        return len(lines.move_id) > 1

    def _reconcile_payment_lines_by_invoice_date(
        self, payment_lines, lines, extra_context=None
    ):
        extra_context = dict(extra_context or {})
        reconcile_domain = [
            ("reconciled", "=", False),
            ("parent_state", "=", "posted"),
        ]
        payment_lines = payment_lines.filtered_domain(reconcile_domain)
        lines = lines.filtered_domain(reconcile_domain)
        if not payment_lines or not lines:
            return
        if not self._should_reconcile_by_invoice_date(lines):
            (payment_lines + lines).with_context(**extra_context).reconcile()
            return
        plan = []
        sorted_moves = lines.move_id.sorted(key=self._get_invoice_date_sort_key)
        for move in sorted_moves:
            move_lines = lines.filtered(lambda line, move=move: line.move_id == move)
            plan.append(payment_lines | move_lines)
        (payment_lines + lines).with_context(**extra_context)._reconcile_plan(plan)

    def _reconcile_payments(self, to_process, edit_mode=False):
        if not self.group_payment:
            return super()._reconcile_payments(to_process, edit_mode=edit_mode)
        domain = [
            ("parent_state", "=", "posted"),
            (
                "account_type",
                "in",
                self.env["account.payment"]._get_valid_payment_account_types(),
            ),
            ("reconciled", "=", False),
        ]
        for vals in to_process:
            payment = vals["payment"]
            payment_lines = payment.move_id.line_ids.filtered_domain(domain)
            lines = vals["to_reconcile"]
            extra_context = {}
            if "rate" in vals:
                extra_context["forced_rate_from_register_payment"] = vals["rate"]
            for account in payment_lines.account_id:
                account_payment_lines = payment_lines.filtered(
                    lambda line, account=account: line.account_id == account
                )
                account_lines = lines.filtered(
                    lambda line, account=account: line.account_id == account
                )
                self._reconcile_payment_lines_by_invoice_date(
                    account_payment_lines,
                    account_lines,
                    extra_context=extra_context,
                )
            lines.move_id.matched_payment_ids = [Command.link(payment.id)]
