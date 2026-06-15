from odoo import models

SENIAT_EXEMPT_REPORT_NAMES = frozenset({
    "pba_easy_commission.rpt_comm_pending",
    "pba_easy_commission.rpt_comm_voucher",
})


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _l10n_ve_is_seniat_exempt_invoice_report(self, report):
        return (report.report_name or "") in SENIAT_EXEMPT_REPORT_NAMES

    def _l10n_ve_is_account_invoice_pdf_report(self, report):
        if self._l10n_ve_is_seniat_exempt_invoice_report(report):
            return False
        return super()._l10n_ve_is_account_invoice_pdf_report(report)

    def _l10n_ve_is_ve_blockable_invoice_report(self, report_ref):
        report = self._get_report(report_ref)
        if self._l10n_ve_is_seniat_exempt_invoice_report(report):
            return False
        return super()._l10n_ve_is_ve_blockable_invoice_report(report_ref)
