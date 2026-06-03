from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    goal_commission_start_date = fields.Date(
        string="Fecha Inicio de Comisiones",
    )
