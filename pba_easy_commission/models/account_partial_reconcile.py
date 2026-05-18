from odoo import models, _
from odoo.exceptions import UserError


class AccountPartialReconcile(models.Model):
    _inherit = 'account.partial.reconcile'

    def unlink(self):
        for partial in self:
            invoice_moves = (partial.debit_move_id.move_id + partial.credit_move_id.move_id).filtered(
                lambda m: m.move_type == 'out_invoice' and m.state == 'posted'
            )
            blocked_invoice = invoice_moves.filtered('commission_line_ids').filtered(
                lambda m: m._has_billed_commission_lines()
            )
            if blocked_invoice:
                raise UserError(_(
                    'No se puede desconciliar pagos en una factura con comisiones ya registradas. Factura: %(invoice)s',
                    invoice=blocked_invoice[0].name or blocked_invoice[0].ref or blocked_invoice[0].id,
                ))
        return super().unlink()
