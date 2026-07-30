from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    show_generate_missing_move = fields.Boolean(
        compute="_compute_show_generate_missing_move",
    )

    @api.depends("move_id", "state")
    def _compute_show_generate_missing_move(self):
        for payment in self:
            payment.show_generate_missing_move = (
                not payment.move_id
                and payment.state in ("draft", "in_process", "paid")
            )

    def action_generate_missing_move(self):
        payments = self.filtered(
            lambda p: not p.move_id and p.state in ("draft", "in_process", "paid")
        )
        if not payments:
            raise UserError(
                _("There are no payments without a journal entry to process.")
            )

        for payment in payments:
            payment._generate_missing_move()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Journal entries generated"),
                "message": _(
                    "%(count)s payment(s) now have a journal entry.",
                    count=len(payments),
                ),
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.client", "tag": "soft_reload"},
            },
        }

    def _generate_missing_move(self):
        self.ensure_one()
        if self.move_id:
            return

        outstanding = self.payment_method_line_id.payment_account_id
        if not outstanding:
            raise UserError(
                _(
                    "Configure the outstanding payments/receipts account on the "
                    "%(method)s payment method of journal %(journal)s before "
                    "generating the entry for payment %(payment)s.",
                    method=self.payment_method_line_id.display_name,
                    journal=self.journal_id.display_name,
                    payment=self.display_name,
                )
            )

        previous_state = self.state
        if previous_state not in ("draft", "canceled"):
            self.write({"state": "draft"})

        self.outstanding_account_id = outstanding
        self._generate_journal_entry()
        if self.move_id and self.move_id.state == "draft":
            self.move_id.action_post()

        self._reconcile_matched_invoices()

        if (
            previous_state == "paid"
            or self.outstanding_account_id.account_type == "asset_cash"
        ):
            self.state = "paid"
        elif self.state != "in_process":
            self.state = "in_process"

    def _reconcile_matched_invoices(self):
        self.ensure_one()
        if not self.move_id or not self.invoice_ids:
            return

        domain = [
            ("parent_state", "=", "posted"),
            ("account_type", "in", self._get_valid_payment_account_types()),
            ("reconciled", "=", False),
        ]
        payment_lines = self.move_id.line_ids.filtered_domain(domain)
        invoice_lines = self.invoice_ids.line_ids.filtered_domain(domain)
        for account in payment_lines.account_id:
            lines = (payment_lines + invoice_lines).filtered(
                lambda line: line.account_id == account
                and not line.reconciled
                and line.parent_state == "posted"
            )
            if lines:
                lines.reconcile()
