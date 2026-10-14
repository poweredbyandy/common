# Copyright 2026 andyengit
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models, tools


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    def _try_auto_reconcile_imported_lines(self):
        lines = self.filtered(lambda line: not line.is_reconciled)
        if not lines:
            return
        cron_limit_time = tools.config["limit_time_real_cron"] or -1
        limit_time = cron_limit_time if 0 < cron_limit_time < 180 else 180
        lines._cron_try_auto_reconcile_statement_lines(limit_time=limit_time)
