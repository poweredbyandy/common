from odoo import _, api, fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    bank_reconciliation_status = fields.Selection(
        selection=[
            ("with_reconciliation", "Bank Reconciliation"),
            ("without_reconciliation", "No Bank Reconciliation"),
            ("not_configured", "Accounts Not Configured"),
        ],
        string="Bank Reconciliation Status",
        compute="_compute_bank_reconciliation_status",
    )

    @api.depends(
        "type",
        "default_account_id",
        "inbound_payment_method_line_ids.payment_account_id",
        "outbound_payment_method_line_ids.payment_account_id",
    )
    def _compute_bank_reconciliation_status(self):
        for journal in self:
            if journal.type not in ("bank", "cash"):
                journal.bank_reconciliation_status = False
                continue

            method_lines = (
                journal.inbound_payment_method_line_ids
                | journal.outbound_payment_method_line_ids
            )
            if not method_lines or any(
                not line.payment_account_id for line in method_lines
            ):
                journal.bank_reconciliation_status = "not_configured"
                continue

            journal_account = journal.default_account_id
            payment_accounts = method_lines.mapped("payment_account_id")
            if journal_account and payment_accounts == journal_account:
                journal.bank_reconciliation_status = "without_reconciliation"
            elif journal_account and journal_account in payment_accounts:
                journal.bank_reconciliation_status = "not_configured"
            else:
                journal.bank_reconciliation_status = "with_reconciliation"

    def action_open_bank_reconciliation_status(self):
        self.ensure_one()
        return {
            "name": _("Bank Reconciliation"),
            "type": "ir.actions.act_window",
            "res_model": "account.journal.bank.reconciliation.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_journal_id": self.id,
                "active_id": self.id,
            },
        }
