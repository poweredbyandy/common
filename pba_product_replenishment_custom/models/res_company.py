from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    pba_replenishment_equivalence_currency_ids = fields.Many2many(
        comodel_name="res.currency",
        relation="res_company_pba_replenishment_equiv_currency_rel",
        column1="company_id",
        column2="currency_id",
        string="Monedas equivalencia (reporte de compras)",
        help="Monedas de equivalencia por defecto al abrir el reporte de compras (editables en el asistente).",
    )
