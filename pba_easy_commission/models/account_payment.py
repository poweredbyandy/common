from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    pba_apply_commission = fields.Boolean(
        string='Aplicar comisión',
        default=True,
        copy=True,
        help='Si está desactivado, este pago no generará comisión para el vendedor.',
    )
