from odoo import api, fields, models


class ReportGoalCommissionPending(models.AbstractModel):
    _name = "report.pba_goal_commision.rpt_goal_comm_pending"
    _description = "Reporte de comisiones por meta pendientes"

    @api.model
    def _get_report_values(self, docids, data=None):
        report_lang = self.env["account.move"]._goal_commission_report_lang()
        env = self.env(context=dict(self.env.context, lang=report_lang))
        partners = env["res.partner"].browse(docids)
        report_date = fields.Date.context_today(self)
        report_date_display = report_date.strftime("%d/%m/%Y") if report_date else ""
        return {
            "doc_ids": docids,
            "doc_model": "res.partner",
            "docs": partners,
            "report_lang": report_lang,
            "report_date": report_date_display,
            "report_data": {partner.id: partner.get_goal_pending_commission_report_data() for partner in partners},
        }


class ReportGoalCommissionPaymentVoucher(models.AbstractModel):
    _name = "report.pba_goal_commision.rpt_goal_comm_voucher"
    _description = "Comprobante de pago de comisiones por meta"

    @api.model
    def _get_report_values(self, docids, data=None):
        report_lang = self.env["account.move"]._goal_commission_report_lang()
        env = self.env(context=dict(self.env.context, lang=report_lang))
        bills = env["account.move"].browse(docids)
        return {
            "doc_ids": docids,
            "doc_model": "account.move",
            "docs": bills,
            "report_lang": report_lang,
            "report_data": {bill.id: bill.get_goal_commission_payment_voucher_data() for bill in bills},
        }
