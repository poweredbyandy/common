from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command


class AccountJournalBankReconciliationWizard(models.TransientModel):
    _name = "account.journal.bank.reconciliation.wizard"
    _description = "Configure Bank Reconciliation on Journal"

    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Journal",
        required=True,
        readonly=True,
    )
    journal_account_id = fields.Many2one(
        related="journal_id.default_account_id",
        string="Journal Account",
    )
    current_status = fields.Selection(
        related="journal_id.bank_reconciliation_status",
        string="Current Status",
    )
    enable_bank_reconciliation = fields.Boolean(
        string="Enable Bank Reconciliation",
        help="If enabled, outstanding receipts and payments accounts are "
        "created (or reused) and assigned to the payment methods. "
        "If disabled, the journal account is used on all payment methods.",
    )
    receipt_account_name = fields.Char(
        string="Outstanding Receipts Account",
        compute="_compute_account_names",
    )
    payment_account_name = fields.Char(
        string="Outstanding Payments Account",
        compute="_compute_account_names",
    )

    @api.depends("journal_id", "journal_id.default_account_id")
    def _compute_account_names(self):
        for wizard in self:
            account_name = wizard.journal_account_id.name or ""
            wizard.receipt_account_name = _(
                "Outstanding Receipts (%s)", account_name
            )
            wizard.payment_account_name = _(
                "Outstanding Payments (%s)", account_name
            )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        journal = self.env["account.journal"].browse(
            self.env.context.get("default_journal_id")
            or self.env.context.get("active_id")
        )
        if journal:
            res["journal_id"] = journal.id
            res["enable_bank_reconciliation"] = (
                journal.bank_reconciliation_status != "without_reconciliation"
            )
        return res

    def action_apply(self):
        self.ensure_one()
        journal = self.journal_id
        if journal.type not in ("bank", "cash"):
            raise UserError(
                _("Bank reconciliation can only be configured on bank or cash journals.")
            )
        if not journal.default_account_id:
            raise UserError(
                _("Configure the journal account before setting bank reconciliation.")
            )
        method_lines = (
            journal.inbound_payment_method_line_ids
            | journal.outbound_payment_method_line_ids
        )
        if not method_lines:
            raise UserError(
                _(
                    "Add at least one incoming or outgoing payment method on "
                    "journal %(journal)s.",
                    journal=journal.display_name,
                )
            )

        if self.enable_bank_reconciliation:
            self._enable_bank_reconciliation()
            message = _(
                "Bank reconciliation enabled on journal %(journal)s.",
                journal=journal.display_name,
            )
            notif_type = "success"
        else:
            self._disable_bank_reconciliation()
            message = _(
                "Bank reconciliation disabled on journal %(journal)s. "
                "Payment methods now use the journal account.",
                journal=journal.display_name,
            )
            notif_type = "warning"

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Bank Reconciliation"),
                "message": message,
                "type": notif_type,
                "sticky": False,
                "next": {"type": "ir.actions.client", "tag": "soft_reload"},
            },
        }

    def _enable_bank_reconciliation(self):
        self.ensure_one()
        journal = self.journal_id
        receipt_account = self._get_or_create_outstanding_account(
            self.receipt_account_name, "receipt"
        )
        payment_account = self._get_or_create_outstanding_account(
            self.payment_account_name, "payment"
        )
        journal.inbound_payment_method_line_ids.write(
            {"payment_account_id": receipt_account.id}
        )
        journal.outbound_payment_method_line_ids.write(
            {"payment_account_id": payment_account.id}
        )

    def _disable_bank_reconciliation(self):
        self.ensure_one()
        journal = self.journal_id
        journal_account = journal.default_account_id
        (
            journal.inbound_payment_method_line_ids
            | journal.outbound_payment_method_line_ids
        ).write({"payment_account_id": journal_account.id})

    def _get_or_create_outstanding_account(self, name, account_kind):
        self.ensure_one()
        journal = self.journal_id
        company = journal.company_id
        Account = self.env["account.account"].with_company(company)
        journal_account_name = journal.default_account_id.name or ""
        if account_kind == "receipt":
            candidate_names = {
                name,
                "Outstanding Receipts (%s)" % journal_account_name,
                "Recibos pendientes (%s)" % journal_account_name,
            }
        else:
            candidate_names = {
                name,
                "Outstanding Payments (%s)" % journal_account_name,
                "Pagos pendientes (%s)" % journal_account_name,
            }
        account = Account.search(
            [
                ("name", "in", list(candidate_names)),
                ("account_type", "=", "asset_current"),
                *Account._check_company_domain(company),
            ],
            limit=1,
        )
        if account:
            if not account.reconcile:
                account.reconcile = True
            return account

        start_code = (
            journal.default_account_id.code
            or company.bank_account_code_prefix
            or "1"
        )
        code = Account._search_new_account_code(start_code, cache={})
        vals = {
            "name": name,
            "code": code,
            "account_type": "asset_current",
            "reconcile": True,
            "company_ids": [Command.link(company.id)],
        }
        if journal.currency_id:
            vals["currency_id"] = journal.currency_id.id
        return Account.create(vals)
