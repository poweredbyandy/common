from odoo import _, api, fields, models
from odoo.exceptions import UserError


class CommissionAdjustmentWizard(models.TransientModel):
    _name = 'commission.adjustment.wizard'
    _description = 'Wizard de ajuste manual de comision'

    invoice_id = fields.Many2one(
        comodel_name='account.move',
        string='Factura',
        required=True,
        readonly=True,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Moneda',
        required=True,
    )
    amount = fields.Monetary(
        string='Monto ajuste',
        currency_field='currency_id',
        required=True,
        help='Use un valor negativo para reducir la comision y positivo para aumentarla.',
    )
    note = fields.Char(
        string='Nota',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        invoice_id = res.get('invoice_id') or self.env.context.get('default_invoice_id')
        if invoice_id:
            invoice = self.env['account.move'].browse(invoice_id)
            if invoice.currency_id:
                res['currency_id'] = invoice.currency_id.id
        return res

    def action_confirm(self):
        self.ensure_one()
        invoice = self.invoice_id
        if invoice.move_type != 'out_invoice' or invoice.state != 'posted':
            raise UserError(_('Solo se pueden registrar ajustes en facturas de cliente confirmadas.'))
        if self.currency_id.is_zero(self.amount):
            raise UserError(_('El monto del ajuste no puede ser cero.'))
        self.env['account.move.commission.adjustment'].create({
            'invoice_id': invoice.id,
            'currency_id': self.currency_id.id,
            'amount': self.amount,
            'note': self.note,
        })
        return {'type': 'ir.actions.act_window_close'}
