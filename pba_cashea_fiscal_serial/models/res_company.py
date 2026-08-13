from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    cashea_fiscal_payment_method_name = fields.Char(
        string="Metodo de pago fiscal Cashea",
        default="Cashea",
        help=(
            "Nombre del metodo de pago enviado a la maquina fiscal "
            "para el monto no pagado de facturas Cashea "
            "(en lugar de Credito)."
        ),
    )
