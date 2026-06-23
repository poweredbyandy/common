from odoo import api, models, _
from odoo.exceptions import UserError


class AccountPartialReconcile(models.Model):
    _inherit = 'account.partial.reconcile'

    @api.model_create_multi
    def create(self, vals_list):
        partials = super().create(vals_list)
        if not self.env.context.get('pba_skip_commission_sync'):
            partials._pba_sync_commission_lines_on_reconcile()
        return partials

    def _pba_sync_commission_lines_on_reconcile(self):
        invoice_moves = self.env['account.move']
        for partial in self:
            invoice_moves |= (partial.debit_move_id.move_id + partial.credit_move_id.move_id).filtered(
                lambda move: move.move_type == 'out_invoice' and move.state == 'posted'
            )
        if not invoice_moves:
            return
        to_rebuild = invoice_moves.filtered(lambda move: not move._has_billed_commission_lines())
        if to_rebuild:
            to_rebuild._pba_rebuild_waiting_commission_lines()
        billed = invoice_moves - to_rebuild
        if billed:
            billed._sync_commission_lines_from_payments()

    def unlink(self):
        if self.env.context.get("pba_skip_commission_unreconcile_check"):
            return super().unlink()
        invoice_moves = self.env['account.move']
        for partial in self:
            partial_invoices = (partial.debit_move_id.move_id + partial.credit_move_id.move_id).filtered(
                lambda m: m.move_type == 'out_invoice' and m.state == 'posted'
            )
            blocked_invoice = partial_invoices.filtered('commission_line_ids').filtered(
                lambda m: m._has_billed_commission_lines()
            )
            if blocked_invoice:
                raise UserError(_(
                    'No se puede desconciliar pagos en una factura con comisiones ya registradas. Factura: %(invoice)s',
                    invoice=blocked_invoice[0].name or blocked_invoice[0].ref or blocked_invoice[0].id,
                ))
            invoice_moves |= partial_invoices
        result = super().unlink()
        to_rebuild = invoice_moves.filtered(lambda move: not move._has_billed_commission_lines())
        if to_rebuild:
            to_rebuild._pba_rebuild_waiting_commission_lines()
        return result
