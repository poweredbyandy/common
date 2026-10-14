# Copyright 2026 andyengit
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class AccountStatementImport(models.TransientModel):
    _inherit = "account.statement.import"

    def _import_file(self):
        result = super()._import_file()
        statements = self.env["account.bank.statement"].browse(result["statement_ids"])
        statements.line_ids._try_auto_reconcile_imported_lines()
        return result
