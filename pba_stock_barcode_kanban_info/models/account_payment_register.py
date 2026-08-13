from odoo import models


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _create_payments(self):
        payments = super()._create_payments()
        invoices = payments.invoice_ids | payments.reconciled_invoice_ids
        if not invoices:
            invoices = self.line_ids.move_id
        invoices._pba_notify_barcode_related_pickings()
        return payments
