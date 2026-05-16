from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class ProductTemplate(models.Model):
    _inherit = "product.template"

    pba_qty_mx = fields.Float(
        string="Vender en múltiplos de",
        digits="Product Unit of Measure",
        help="Si se indica un valor mayor que cero, la cantidad vendida o facturada debe ser múltiplo de este número.",
    )

    @api.constrains("pba_qty_mx")
    def _check_pba_qty_mx(self):
        for product in self:
            if product.pba_qty_mx < 0:
                raise ValidationError(_("El múltiplo de venta no puede ser negativo."))
