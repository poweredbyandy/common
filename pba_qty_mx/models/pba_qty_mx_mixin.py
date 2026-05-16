from odoo import _
from odoo.exceptions import ValidationError
from odoo.models import AbstractModel
from odoo.tools import float_compare, float_is_zero


class PbaQtyMxMixin(AbstractModel):
    _name = "pba.qty.mx.mixin"
    _description = "PBA quantity multiple mixin"

    def _pba_qty_mx_is_valid(self, qty, multiple, rounding):
        if not multiple or multiple <= 0:
            return True
        if float_compare(qty, 0, precision_rounding=rounding) <= 0:
            return False
        if float_compare(qty, multiple, precision_rounding=rounding) < 0:
            return False
        ratio = qty / multiple
        return float_is_zero(ratio - round(ratio), precision_rounding=rounding)

    def _pba_qty_mx_raise_validation_error(self, product, qty, multiple):
        raise ValidationError(
            _(
                'La cantidad %(qty)s del producto "%(product)s" debe ser un múltiplo de %(multiple)s (mínimo %(multiple)s).',
                qty=qty,
                product=product.display_name,
                multiple=multiple,
            )
        )
