from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountMoveCommissionAdjustment(models.Model):
    _name = 'account.move.commission.adjustment'
    _description = 'Ajuste manual de comision'
    _inherit = ['mail.thread']
    _order = 'id asc'

    invoice_id = fields.Many2one(
        comodel_name='account.move',
        string='Factura',
        required=True,
        ondelete='cascade',
        tracking=True,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        required=True,
        tracking=True,
    )
    amount = fields.Monetary(
        string='Monto ajuste',
        currency_field='currency_id',
        required=True,
        tracking=True,
        help='Monto positivo aumenta la comision; monto negativo la reduce.',
    )
    note = fields.Char(
        string='Nota',
        tracking=True,
    )
    description = fields.Char(
        compute='_compute_description',
        store=True,
        readonly=True,
    )
    state = fields.Selection(
        selection=[
            ('waiting', 'En espera'),
            ('invoiced', 'Facturada'),
            ('paid', 'Pagada'),
        ],
        default='waiting',
        required=True,
        tracking=True,
    )
    vendor_bill_id = fields.Many2one(
        comodel_name='account.move',
        string='Factura proveedor',
        domain=[('move_type', '=', 'in_invoice')],
        tracking=True,
    )

    @api.depends('amount', 'currency_id', 'invoice_id', 'note')
    def _compute_description(self):
        for adjustment in self:
            invoice = adjustment.invoice_id
            invoice_label = invoice.name or invoice.ref or str(invoice.id)
            currency_name = adjustment.currency_id.name or ''
            abs_amount = abs(adjustment.amount)
            base_desc = _(
                'Ajuste de comision de %(amount)s %(currency)s sobre factura %(invoice)s',
                amount='{:,.2f}'.format(abs_amount),
                currency=currency_name,
                invoice=invoice_label,
            )
            if adjustment.note:
                adjustment.description = '%s (%s)' % (base_desc, adjustment.note)
            else:
                adjustment.description = base_desc

    @api.constrains('amount')
    def _check_amount_not_zero(self):
        for adjustment in self:
            if adjustment.currency_id.is_zero(adjustment.amount):
                raise ValidationError(_('El monto del ajuste no puede ser cero.'))

    @api.constrains('invoice_id', 'state')
    def _check_invoice_state(self):
        for adjustment in self:
            invoice = adjustment.invoice_id
            if invoice.move_type != 'out_invoice' or invoice.state != 'posted':
                raise ValidationError(_('Los ajustes solo pueden registrarse en facturas de cliente confirmadas.'))

    @api.model_create_multi
    def create(self, vals_list):
        adjustments = super().create(vals_list)
        adjustments.invoice_id._recompute_seller_commission_pending_stats()
        return adjustments

    def write(self, vals):
        if 'vendor_bill_id' in vals and not vals.get('vendor_bill_id'):
            vals['state'] = 'waiting'
        elif vals.get('vendor_bill_id') and 'state' not in vals:
            vals['state'] = 'invoiced'
        result = super().write(vals)
        self.invoice_id._recompute_seller_commission_pending_stats()
        return result

    def unlink(self):
        billed = self.filtered(lambda adj: adj.vendor_bill_id or adj.state in ('invoiced', 'paid'))
        if billed:
            raise UserError(_('No se pueden eliminar ajustes de comision ya facturados.'))
        invoices = self.invoice_id
        result = super().unlink()
        invoices._recompute_seller_commission_pending_stats()
        return result
