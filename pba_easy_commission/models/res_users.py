from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class ResUsers(models.Model):
    _inherit = 'res.users'

    commission_percent = fields.Float(
        string='Porcentaje de Comision',
        tracking=True,
        default=0.0,
    )
    commission_pending_invoice_count = fields.Integer(
        string='Facturas Pendientes',
        compute='_compute_commission_pending_stats',
        store=True,
    )
    commission_pending_display = fields.Char(
        string='Total Pendiente',
        compute='_compute_commission_pending_stats',
        store=True,
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

    @api.model
    def init_commission_pending_stats(self):
        sellers = self.sudo().search([('share', '=', False)])
        if sellers:
            sellers._compute_commission_pending_stats()

    @api.depends('active', 'share')
    def _compute_commission_pending_stats(self):
        for user in self:
            user.commission_pending_invoice_count = 0
            user.commission_pending_display = '—'
        if not self.ids:
            return
        pending_by_user = {user.id: {'count': 0, 'totals': {}} for user in self}
        invoices = self.env['account.move'].search([
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('commission_available', '=', True),
            ('invoice_user_id', 'in', self.ids),
        ])
        for invoice in invoices:
            user_id = invoice.invoice_user_id.id
            if user_id not in pending_by_user:
                continue
            pending_by_user[user_id]['count'] += 1
            currency = invoice.currency_id.name
            pending_by_user[user_id]['totals'][currency] = (
                pending_by_user[user_id]['totals'].get(currency, 0.0) + invoice.commission_amount_total
            )
        for user in self:
            stats = pending_by_user[user.id]
            user.commission_pending_invoice_count = stats['count']
            if stats['totals']:
                user.commission_pending_display = ' · '.join(
                    '%s %s' % ('{:,.2f}'.format(amount), currency)
                    for currency, amount in sorted(stats['totals'].items())
                )
            else:
                user.commission_pending_display = '—'

    def action_open_seller_partner(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_('El usuario no tiene contacto vinculado.'))
        return {
            'name': self.partner_id.display_name,
            'type': 'ir.actions.act_window',
            'res_model': 'res.partner',
            'res_id': self.partner_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_refresh_seller_commissions(self):
        for user in self:
            if user.partner_id:
                user.partner_id.action_refresh_seller_pending_commissions()
        return True

    def action_open_pending_commissions(self):
        self.ensure_one()
        return {
            'name': _('Comisiones Pendientes'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('pba_easy_commission.view_move_tree_customer_commissions').id, 'list'),
                (False, 'form'),
            ],
            'domain': [
                ('move_type', '=', 'out_invoice'),
                ('state', '=', 'posted'),
                ('invoice_user_id', '=', self.id),
                ('commission_available', '=', True),
            ],
            'context': {'default_move_type': 'out_invoice'},
        }

    def action_pay_pending_commissions(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_('El usuario no tiene contacto vinculado.'))
        return self.partner_id.action_pay_pending_commissions()

    def action_print_pending_commissions(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError(_('El usuario no tiene contacto vinculado.'))
        return self.partner_id.action_print_pending_commissions()

    def write(self, vals):
        protected_fields = {'commission_percent', 'commission_billing_periodicity', 'commission_billing_day'}
        if protected_fields.intersection(vals.keys()) and not self.env.user.has_group('pba_easy_commission.group_commission_admin'):
            raise AccessError(_('Solo el grupo Administrador de comisiones puede modificar configuraciones de comision del vendedor.'))
        result = super().write(vals)
        if 'commission_percent' in vals and self.env.user.has_group('pba_easy_commission.group_commission_admin'):
            for user in self.filtered('partner_id'):
                user.partner_id.sudo().write({'commission_percent': user.commission_percent})
        return result
