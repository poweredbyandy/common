from odoo import _, fields, models
from odoo.exceptions import AccessError


class ResPartner(models.Model):
    _inherit = 'res.partner'

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

    def write(self, vals):
        protected_fields = {'commission_percent', 'commission_billing_periodicity', 'commission_billing_day'}
        if protected_fields.intersection(vals.keys()) and not self.env.user.has_group('pba_easy_commission.group_commission_admin'):
            raise AccessError(_('Solo el grupo Administrador de comisiones puede modificar configuraciones de comision del vendedor.'))
        return super().write(vals)
