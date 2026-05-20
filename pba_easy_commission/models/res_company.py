from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    commission_product_id = fields.Many2one(
        comodel_name='product.product',
        string='Producto de Comision',
        tracking=True,
        domain=[('type', '=', 'service')],
    )
    commission_excluded_journal_ids = fields.Many2many(
        comodel_name='account.journal',
        string='Diarios Excluidos para Comisiones',
        tracking=True,
    )
    commission_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Diario de Comisiones',
        tracking=True,
        domain="[('type', '=', 'purchase'), ('company_id', '=', company_id)]",
    )
