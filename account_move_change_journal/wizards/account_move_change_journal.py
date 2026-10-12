from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError


class AccountMoveChangeJournal(models.TransientModel):
    _name = "account.move.change.journal"
    _description = "Change Journal of Posted Invoices"

    move_ids = fields.Many2many(
        "account.move",
        string="Invoices",
        required=True,
        readonly=True,
    )
    company_id = fields.Many2one(
        "res.company",
        compute="_compute_company_id",
    )
    journal_type = fields.Selection(
        selection=[("sale", "Sales"), ("purchase", "Purchase")],
        compute="_compute_journal_type",
    )
    available_journal_ids = fields.Many2many(
        "account.journal",
        compute="_compute_available_journal_ids",
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="New Journal",
        required=True,
        domain="[('id', 'in', available_journal_ids)]",
    )

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        if self.env.context.get("active_model") != "account.move":
            return values
        moves = self.env["account.move"].browse(
            self.env.context.get("active_ids") or []
        )
        self._check_moves(moves)
        values["move_ids"] = [Command.set(moves.ids)]
        return values

    @api.depends("move_ids")
    def _compute_company_id(self):
        for wizard in self:
            wizard.company_id = wizard.move_ids[:1].company_id

    @api.depends("move_ids")
    def _compute_journal_type(self):
        for wizard in self:
            wizard.journal_type = self._get_move_journal_type(wizard.move_ids[:1])

    @api.depends("move_ids", "company_id", "journal_type")
    def _compute_available_journal_ids(self):
        for wizard in self:
            if not wizard.move_ids:
                wizard.available_journal_ids = False
                continue
            wizard.available_journal_ids = self.env["account.journal"].search(
                [
                    *self.env["account.journal"]._check_company_domain(
                        wizard.company_id
                    ),
                    ("type", "=", wizard.journal_type),
                    ("id", "not in", wizard.move_ids.journal_id.ids),
                ]
            )

    @api.model
    def _get_move_journal_type(self, move):
        if move.is_sale_document(include_receipts=True):
            return "sale"
        if move.is_purchase_document(include_receipts=True):
            return "purchase"
        return False

    @api.model
    def _check_moves(self, moves):
        if not moves:
            raise UserError(_("Select at least one invoice."))
        not_invoices = moves.filtered(lambda move: not move.is_invoice(True))
        if not_invoices:
            raise UserError(
                _(
                    "Only customer and vendor invoices can change journal:\n%s",
                    "\n".join(not_invoices.mapped("display_name")),
                )
            )
        not_posted = moves.filtered(lambda move: move.state != "posted")
        if not_posted:
            raise UserError(
                _(
                    "Only posted invoices can change journal:\n%s",
                    "\n".join(not_posted.mapped("display_name")),
                )
            )
        hashed = moves.filtered("inalterable_hash")
        if hashed:
            raise UserError(
                _(
                    "These invoices are protected by a hash and cannot change "
                    "journal:\n%s",
                    "\n".join(hashed.mapped("display_name")),
                )
            )
        if len(moves.company_id) > 1:
            raise UserError(_("All invoices must belong to the same company."))
        if len({self._get_move_journal_type(move) for move in moves}) > 1:
            raise UserError(
                _("Do not mix customer and vendor invoices in the same change.")
            )

    def _check_journal(self, move):
        self.ensure_one()
        journal = self.journal_id
        if journal == move.journal_id:
            raise UserError(
                _(
                    "%(move)s is already in journal %(journal)s.",
                    move=move.display_name,
                    journal=journal.display_name,
                )
            )
        if journal.type != self._get_move_journal_type(move):
            raise UserError(
                _(
                    "Journal %(journal)s does not match the type of %(move)s.",
                    journal=journal.display_name,
                    move=move.display_name,
                )
            )
        if journal.currency_id and journal.currency_id != move.currency_id:
            raise UserError(
                _(
                    "Journal %(journal)s only accepts %(currency)s and %(move)s "
                    "is in %(move_currency)s.",
                    journal=journal.display_name,
                    currency=journal.currency_id.name,
                    move=move.display_name,
                    move_currency=move.currency_id.name,
                )
            )

    def _get_account_line_commands(self, move):
        self.ensure_one()
        old_account = move.journal_id.default_account_id
        new_account = self.journal_id.default_account_id
        if not old_account or not new_account or old_account == new_account:
            return []
        lines = move.line_ids.filtered(
            lambda line: line.display_type == "product"
            and line.account_id == old_account
        )
        return [
            Command.update(line.id, {"account_id": new_account.id}) for line in lines
        ]

    def action_change_journal(self):
        self.ensure_one()
        self._check_moves(self.move_ids)
        for move in self.move_ids:
            self._check_journal(move)
            old_journal = move.journal_id
            old_name = move.name
            vals = {"journal_id": self.journal_id.id, "name": "/"}
            line_commands = self._get_account_line_commands(move)
            if line_commands:
                vals["line_ids"] = line_commands
            move.with_context(skip_readonly_check=True).write(vals)
            if not move.name or move.name == "/":
                move._compute_name()
            move.message_post(
                body=_(
                    "Journal changed from %(old_journal)s to %(new_journal)s. "
                    "Previous number: %(old_name)s.",
                    old_journal=old_journal.display_name,
                    new_journal=self.journal_id.display_name,
                    old_name=old_name,
                )
            )
        return {"type": "ir.actions.act_window_close"}
