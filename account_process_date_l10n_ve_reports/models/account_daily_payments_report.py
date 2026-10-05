from odoo import models


class DailyPaymentsReportCustomHandler(models.AbstractModel):
    _inherit = "account.daily.payments.report.handler.oca"

    def _get_move_validation_date(self, move):
        if move.l10n_ve_process_date:
            return move.l10n_ve_process_date
        payment = self._get_move_payment(move)
        if payment and payment.l10n_ve_process_date:
            return payment.l10n_ve_process_date
        return super()._get_move_validation_date(move)
