from odoo import api, fields, models

from odoo.addons.payment_pagomovil import const
from odoo.addons.payment_pagomovil.models.pagomovil import normalize_phone, normalize_vat


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[("pagomovil", "Pago Móvil")],
        ondelete={"pagomovil": "set default"},
    )
    pagomovil_phone = fields.Char(
        string="Teléfono",
        help="Teléfono al que el cliente debe enviar el pago móvil.",
        required_if_provider="pagomovil",
    )
    pagomovil_vat = fields.Char(
        string="RIF",
        help="RIF o cédula de quien recibe el pago móvil.",
        required_if_provider="pagomovil",
    )
    pagomovil_bank = fields.Char(
        string="Banco",
        help="Banco donde se recibe el pago móvil.",
        required_if_provider="pagomovil",
    )
    pagomovil_holder = fields.Char(
        string="Titular",
        help="Nombre del titular que se muestra al cliente.",
    )

    def _pagomovil_bank_options(self):
        """Return the banks the customer can choose as the origin of the transfer."""
        return const.PAGOMOVIL_BANKS

    def _should_build_inline_form(self, is_validation=False):
        if self.code == "pagomovil" and is_validation:
            return False
        return super()._should_build_inline_form(is_validation=is_validation)

    def _get_default_payment_method_codes(self):
        default_codes = super()._get_default_payment_method_codes()
        if self.code != "pagomovil":
            return default_codes
        return const.DEFAULT_PAYMENT_METHOD_CODES

    @api.model_create_multi
    def create(self, vals_list):
        normalized = [self._pagomovil_normalize_config(vals) for vals in vals_list]
        return super().create(normalized)

    def write(self, vals):
        vals = self._pagomovil_normalize_config(vals)
        return super().write(vals)

    @api.model
    def _pagomovil_normalize_config(self, vals):
        vals = dict(vals)
        if vals.get("pagomovil_phone"):
            vals["pagomovil_phone"] = normalize_phone(vals["pagomovil_phone"])
        if vals.get("pagomovil_vat"):
            vals["pagomovil_vat"] = normalize_vat(vals["pagomovil_vat"])
        if vals.get("pagomovil_bank"):
            vals["pagomovil_bank"] = vals["pagomovil_bank"].strip()
        if vals.get("pagomovil_holder"):
            vals["pagomovil_holder"] = vals["pagomovil_holder"].strip()
        return vals
