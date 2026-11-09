from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    crm_expected_currency_id = fields.Many2one(
        "res.currency",
        string="Moneda del ingreso esperado",
        help="Moneda por defecto del ingreso esperado en las oportunidades. Si queda vacía, se usa la moneda de la compañía.",
    )
