from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    excess_refund_invoice_id = fields.Many2one(
        comodel_name="account.move",
        string="Excess Refund Invoice",
        copy=False,
        index="btree_not_null",
        check_company=True,
    )
    excess_refund_line_id = fields.Many2one(
        comodel_name="account.move.line",
        string="Excess Refund Line",
        copy=False,
        index="btree_not_null",
        check_company=True,
    )
    excess_refund_source_payment_id = fields.Many2one(
        comodel_name="account.payment",
        string="Source Excess Payment",
        copy=False,
        index="btree_not_null",
        check_company=True,
    )

    @api.model
    def _get_valid_payment_account_types(self):
        account_types = super()._get_valid_payment_account_types()
        extra_types = self.env.context.get("excess_refund_account_types") or []
        if not extra_types:
            return account_types
        return list(dict.fromkeys(list(account_types) + list(extra_types)))

    def _excess_refund_cancel_payments(self):
        for payment in self:
            if payment.state == "canceled":
                continue
            if payment.state != "draft":
                payment.action_draft()
            payment.action_cancel()

    def action_excess_refund_cancel(self):
        self._excess_refund_cancel_payments()
        return True

