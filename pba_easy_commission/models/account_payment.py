from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    pba_apply_commission = fields.Boolean(
        string='Aplicar comisión',
        default=True,
        copy=True,
        help='Si está desactivado, este pago no generará comisión para el vendedor.',
    )

    def _pba_sync_commissions_after_apply_change(self):
        invoices = self.mapped('reconciled_invoice_ids').filtered(
            lambda move: move.move_type == 'out_invoice' and move.state == 'posted'
        )
        disabled_payments = self.filtered(lambda payment: not payment.pba_apply_commission)
        for invoice in invoices:
            if invoice._has_billed_commission_lines():
                invoice.commission_line_ids.filtered(
                    lambda line: line.payment_id in disabled_payments
                    and line.state == 'waiting'
                    and not line.vendor_bill_id
                ).unlink()
                invoice._sync_commission_lines_from_payments()
            else:
                invoice._pba_rebuild_waiting_commission_lines()

    def write(self, vals):
        result = super().write(vals)
        if 'pba_apply_commission' in vals:
            self._pba_sync_commissions_after_apply_change()
        return result
