from odoo import models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def action_post(self):
        result = super().action_post()
        invoices = self.invoice_ids | self.reconciled_invoice_ids
        invoices._pba_notify_barcode_related_pickings()
        return result

    def action_validate(self):
        result = super().action_validate()
        invoices = self.invoice_ids | self.reconciled_invoice_ids
        invoices._pba_notify_barcode_related_pickings()
        return result
