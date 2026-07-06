from odoo import fields, models


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    pba_apply_commission = fields.Boolean(
        string='Aplicar comisión',
        default=True,
        help='Si está desactivado, este pago no generará comisión para el vendedor.',
    )

    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = super()._create_payment_vals_from_wizard(batch_result)
        payment_vals['pba_apply_commission'] = self.pba_apply_commission
        return payment_vals

    def _create_payment_vals_from_batch(self, batch_result):
        payment_vals = super()._create_payment_vals_from_batch(batch_result)
        payment_vals['pba_apply_commission'] = self.pba_apply_commission
        return payment_vals
