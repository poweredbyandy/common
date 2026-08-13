from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    cashea_fiscal_payment_method_id = fields.Many2one(
        comodel_name="l10n.ve.fiscal.payment.method",
        string="Metodo de pago fiscal Cashea",
        check_company=True,
        domain="[('company_id', '=', id)]",
        help=(
            "Metodo de pago fiscal TFHKA (codigo 01-24, p. ej. 15 o 16) "
            "usado al imprimir facturas Cashea cuando no hay pagos "
            "conciliados."
        ),
    )
