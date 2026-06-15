from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = "res.partner"

    pba_early_payment_discount_percent = fields.Float(
        string="Descuento pronto pago (%)",
        digits="Discount",
        help="Porcentaje de descuento por pronto pago aplicado por defecto en facturas de cliente.",
    )
    pba_early_payment_discount_days = fields.Integer(
        string="Días pronto pago",
        help="Días desde la fecha de factura para aplicar el descuento por pronto pago.",
    )
    pba_supplier_early_payment_discount_percent = fields.Float(
        string="Descuento pronto pago proveedor (%)",
        digits="Discount",
        help="Porcentaje de descuento por pronto pago aplicado por defecto en facturas de proveedor.",
    )
    pba_supplier_early_payment_discount_days = fields.Integer(
        string="Días pronto pago proveedor",
        help="Días desde la fecha de factura para aplicar el descuento por pronto pago al proveedor.",
    )

    @api.constrains(
        "pba_early_payment_discount_percent",
        "pba_early_payment_discount_days",
        "pba_supplier_early_payment_discount_percent",
        "pba_supplier_early_payment_discount_days",
    )
    def _check_pba_early_payment_discount(self):
        for partner in self:
            if partner.pba_early_payment_discount_percent < 0:
                raise ValidationError(
                    "El descuento por pronto pago del cliente no puede ser negativo."
                )
            if partner.pba_supplier_early_payment_discount_percent < 0:
                raise ValidationError(
                    "El descuento por pronto pago del proveedor no puede ser negativo."
                )
            if partner.pba_early_payment_discount_percent and partner.pba_early_payment_discount_days <= 0:
                raise ValidationError(
                    "Debe indicar los días de pronto pago para el cliente."
                )
            if partner.pba_supplier_early_payment_discount_percent and partner.pba_supplier_early_payment_discount_days <= 0:
                raise ValidationError(
                    "Debe indicar los días de pronto pago para el proveedor."
                )
