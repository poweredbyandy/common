from odoo import _, fields, models
from odoo.exceptions import UserError


class CommissionBillingWizard(models.TransientModel):
    _name = 'commission.billing.wizard'
    _description = 'Wizard de Facturacion de Comisiones'

    invoice_ids = fields.Many2many(
        comodel_name='account.move',
        string='Facturas',
    )
    mode = fields.Selection(
        selection=[
            ('standard', 'Separar por moneda (estandar)'),
            ('convert_to_single', 'Convertir todo a una sola moneda'),
            ('only_single_currency', 'Facturar solo una moneda'),
        ],
        string='Modo de Facturacion',
        default='standard',
        required=True,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Moneda Objetivo',
    )

    def action_confirm(self):
        self.ensure_one()
        invoices = self.invoice_ids.filtered(lambda m: m.move_type == 'out_invoice')
        if not invoices:
            raise UserError(_('Debe seleccionar al menos una factura de cliente para comisionar.'))
        if self.mode in ('convert_to_single', 'only_single_currency') and not self.currency_id:
            raise UserError(_('Debe indicar la moneda para el modo seleccionado.'))

        return invoices.action_create_commission_vendor_bills(
            mode=self.mode,
            selected_currency=self.currency_id,
        )
