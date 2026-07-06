from odoo import _, api, fields, models
from odoo.exceptions import UserError


class CommissionBillingWizardLine(models.TransientModel):
    _name = 'commission.billing.wizard.line'
    _description = 'Linea seleccionable del wizard de comisiones'
    _order = 'invoice_date desc, invoice_id, id'

    wizard_id = fields.Many2one(
        comodel_name='commission.billing.wizard',
        required=True,
        ondelete='cascade',
    )
    commission_line_id = fields.Many2one(
        comodel_name='account.move.commission.line',
        required=True,
        readonly=True,
        ondelete='cascade',
    )
    selected = fields.Boolean(
        string='Facturar',
        default=True,
    )
    invoice_id = fields.Many2one(
        related='commission_line_id.invoice_id',
        readonly=True,
    )
    invoice_date = fields.Date(
        related='invoice_id.invoice_date',
        readonly=True,
    )
    invoice_name = fields.Char(
        related='invoice_id.name',
        readonly=True,
    )
    partner_id = fields.Many2one(
        related='invoice_id.partner_id',
        readonly=True,
    )
    sale_amount = fields.Monetary(
        related='invoice_id.amount_total',
        currency_field='sale_currency_id',
        readonly=True,
    )
    sale_currency_id = fields.Many2one(
        related='invoice_id.currency_id',
        readonly=True,
    )
    payment_amount = fields.Monetary(
        related='commission_line_id.payment_amount',
        readonly=True,
    )
    commission_percent = fields.Float(
        related='commission_line_id.commission_percent',
        readonly=True,
    )
    commission_amount = fields.Monetary(
        related='commission_line_id.commission_amount',
        readonly=True,
    )
    currency_id = fields.Many2one(
        related='commission_line_id.currency_id',
        readonly=True,
    )
    description = fields.Char(
        related='commission_line_id.description',
        readonly=True,
    )


class CommissionBillingWizard(models.TransientModel):
    _name = 'commission.billing.wizard'
    _description = 'Wizard de Facturacion de Comisiones'

    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Vendedor',
        readonly=True,
    )
    invoice_ids = fields.Many2many(
        comodel_name='account.move',
        string='Facturas',
    )
    line_ids = fields.One2many(
        comodel_name='commission.billing.wizard.line',
        inverse_name='wizard_id',
        string='Lineas de comision',
    )
    total_summary = fields.Char(
        string='Total seleccionado',
        compute='_compute_total_summary',
    )
    mode = fields.Selection(
        selection=[
            ('standard', 'Separar por moneda (estandar)'),
        ],
        string='Modo de Facturacion',
        default='standard',
        required=True,
    )
    currency_id = fields.Many2one(
        comodel_name='res.currency',
        string='Moneda Objetivo',
    )

    @api.model
    def _get_default_invoice_ids(self, default_res=None):
        if default_res and default_res.get('invoice_ids'):
            invoice_value = default_res['invoice_ids']
            if isinstance(invoice_value, list):
                if invoice_value and isinstance(invoice_value[0], int):
                    return invoice_value
                for command in invoice_value:
                    if isinstance(command, (list, tuple)) and len(command) >= 3 and command[0] == 6:
                        return command[2]
        context_commands = self.env.context.get('default_invoice_ids')
        if context_commands and isinstance(context_commands, list):
            for command in context_commands:
                if isinstance(command, (list, tuple)) and len(command) >= 3 and command[0] == 6:
                    return command[2]
        return []

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'line_ids' not in fields_list:
            return res
        invoice_ids = self._get_default_invoice_ids(res)
        if not invoice_ids:
            return res
        invoices = self.env['account.move'].browse(invoice_ids).filtered(
            lambda move: move.move_type == 'out_invoice' and move.state == 'posted'
        )
        if invoices:
            invoices._sync_commission_lines_from_payments()
        line_commands = []
        for invoice in invoices.sorted(
            key=lambda move: move.invoice_date or fields.Date.today(),
            reverse=True,
        ):
            waiting_lines = invoice.commission_line_ids.filtered(
                lambda line: line.state == 'waiting' and not line.vendor_bill_id
            )
            for line in waiting_lines:
                line_commands.append((0, 0, {
                    'commission_line_id': line.id,
                    'selected': True,
                }))
        res['line_ids'] = line_commands
        return res

    @api.depends('line_ids.selected', 'line_ids.commission_amount', 'line_ids.currency_id')
    def _compute_total_summary(self):
        for wizard in self:
            totals = {}
            for line in wizard.line_ids.filtered('selected'):
                currency = line.currency_id.name
                totals[currency] = totals.get(currency, 0.0) + line.commission_amount
            wizard.total_summary = ' · '.join(
                '%s %s' % ('{:,.2f}'.format(amount), currency)
                for currency, amount in sorted(totals.items())
            ) or _('0,00')

    def _get_selected_commission_lines(self):
        self.ensure_one()
        return self.line_ids.filtered('selected').mapped('commission_line_id')

    def _action_reload_wizard(self):
        self.ensure_one()
        return {
            'name': _('Pagar Comisiones'),
            'type': 'ir.actions.act_window',
            'res_model': 'commission.billing.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_select_all(self):
        self.ensure_one()
        self.line_ids.write({'selected': True})
        return self._action_reload_wizard()

    def action_deselect_all(self):
        self.ensure_one()
        self.line_ids.write({'selected': False})
        return self._action_reload_wizard()

    def action_toggle_commission_line(self, commission_line_id):
        self.ensure_one()
        wizard_line = self.line_ids.filtered(
            lambda line: line.commission_line_id.id == commission_line_id
        )
        if wizard_line:
            wizard_line.selected = not wizard_line.selected
        return False

    def action_confirm(self):
        self.ensure_one()
        selected_lines = self._get_selected_commission_lines()
        if not selected_lines:
            raise UserError(_('Debe seleccionar al menos una linea de comision para facturar.'))

        invoices = selected_lines.mapped('invoice_id')
        return invoices.with_context(
            pba_commission_line_ids=selected_lines.ids,
        ).action_create_commission_vendor_bills(mode='standard')
