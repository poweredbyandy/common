from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_commission_seller = fields.Boolean(
        compute='_compute_is_commission_seller',
    )
    commission_percent = fields.Float(
        string='Porcentaje de Comision',
        tracking=True,
        default=0.0,
    )
    commission_billing_periodicity = fields.Selection(
        selection=[
            ('daily', 'Diaria'),
            ('monthly', 'Mensual'),
        ],
        string='Periodicidad de Facturacion de Comision',
        default='daily',
        tracking=True,
    )
    commission_billing_day = fields.Integer(
        string='Dia de Facturacion del Mes',
        default=1,
        tracking=True,
    )

    @api.depends('user_ids', 'user_ids.share', 'user_ids.active')
    def _compute_is_commission_seller(self):
        for partner in self:
            partner.is_commission_seller = bool(partner.user_ids.filtered(lambda user: not user.share and user.active))

    def _get_commission_seller_users(self):
        self.ensure_one()
        return self.user_ids.filtered(lambda user: not user.share and user.active)

    def _get_pending_commission_invoices(self):
        self.ensure_one()
        users = self._get_commission_seller_users()
        if not users:
            return self.env['account.move']
        return self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('invoice_user_id', 'in', users.ids),
            ('commission_available', '=', True),
        ])

    def _get_commission_refreshable_invoices(self):
        self.ensure_one()
        users = self._get_commission_seller_users()
        if not users:
            return self.env['account.move']
        invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('invoice_user_id', 'in', users.ids),
            ('payment_state', 'in', ('paid', 'partial', 'in_payment')),
        ])
        return invoices.filtered(lambda move: not move._has_billed_commission_lines())

    def _prepare_pending_commission_invoice_data(self, invoice):
        preview = invoice.prepare_commission_preview_data()
        preview['invoice'] = invoice
        return preview

    def get_pending_commission_report_data(self):
        self.ensure_one()
        invoices = [
            self._prepare_pending_commission_invoice_data(invoice)
            for invoice in self._get_pending_commission_invoices()
        ]
        totals = {}
        for invoice_data in invoices:
            currency = invoice_data['currency']
            totals[currency] = totals.get(currency, 0.0) + invoice_data['amount']
        return {
            'invoices': invoices,
            'invoice_count': len(invoices),
            'totals': [
                {'currency': currency, 'amount': amount}
                for currency, amount in sorted(totals.items())
            ],
            'has_data': bool(invoices),
        }

    def action_refresh_seller_pending_commissions(self):
        self.ensure_one()
        if not self._get_commission_seller_users():
            raise UserError(_('Este contacto no esta vinculado a un usuario vendedor interno.'))
        invoices = self._get_commission_refreshable_invoices()
        if not invoices:
            raise UserError(_('No hay facturas pendientes de comision para actualizar.'))
        refreshed = 0
        skipped = []
        for invoice in invoices:
            try:
                invoice.action_refresh_commission_lines()
                refreshed += 1
            except UserError as error:
                skipped.append('%s: %s' % (invoice.name or invoice.id, error.args[0]))
        message = _('Se actualizaron %(count)s factura(s).', count=refreshed)
        if skipped:
            message = '%s\n%s' % (message, '\n'.join(skipped))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Actualizar comision'),
                'message': message,
                'type': 'success' if refreshed else 'warning',
                'sticky': bool(skipped),
            },
        }

    def action_pay_pending_commissions(self):
        self.ensure_one()
        invoices = self._get_pending_commission_invoices()
        if not invoices:
            raise UserError(_('No hay comisiones pendientes para facturar a este vendedor.'))
        return {
            'name': _('Pagar Comisiones'),
            'type': 'ir.actions.act_window',
            'res_model': 'commission.billing.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_invoice_ids': [(6, 0, invoices.ids)],
                'default_partner_id': self.id,
            },
        }

    def action_print_pending_commissions(self):
        self.ensure_one()
        if not self._get_pending_commission_invoices():
            raise UserError(_('No hay comisiones pendientes para imprimir.'))
        return self.env.ref('pba_easy_commission.action_report_commission_pending').report_action(self)

    def write(self, vals):
        protected_fields = {'commission_percent', 'commission_billing_periodicity', 'commission_billing_day'}
        if protected_fields.intersection(vals.keys()) and not self.env.user.has_group('pba_easy_commission.group_commission_admin'):
            raise AccessError(_('Solo el grupo Administrador de comisiones puede modificar configuraciones de comision del vendedor.'))
        return super().write(vals)
