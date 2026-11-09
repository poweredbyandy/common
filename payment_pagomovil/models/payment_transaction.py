from odoo import _, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import format_amount

from odoo.addons.payment_pagomovil.const import PAGOMOVIL_BANKS
from odoo.addons.payment_pagomovil.models.pagomovil import (
    normalize_bank,
    normalize_phone,
    normalize_reference,
    normalize_vat,
    prepare_receipt,
)


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    pagomovil_vat = fields.Char(string="RIF o cédula", readonly=True, copy=False)
    pagomovil_phone = fields.Char(string="Teléfono", readonly=True, copy=False)
    pagomovil_bank = fields.Selection(
        selection=PAGOMOVIL_BANKS,
        string="Banco",
        readonly=True,
        copy=False,
    )
    pagomovil_reference = fields.Char(
        string="Referencia del pago", readonly=True, copy=False
    )
    pagomovil_receipt = fields.Binary(
        string="Comprobante", readonly=True, copy=False, attachment=True
    )
    pagomovil_receipt_filename = fields.Char(
        string="Nombre del comprobante", readonly=True, copy=False
    )
    pagomovil_destination_holder = fields.Char(
        string="Titular de destino", readonly=True, copy=False
    )
    pagomovil_destination_vat = fields.Char(
        string="RIF de destino", readonly=True, copy=False
    )
    pagomovil_destination_phone = fields.Char(
        string="Teléfono de destino", readonly=True, copy=False
    )
    pagomovil_destination_bank = fields.Char(
        string="Banco de destino", readonly=True, copy=False
    )

    def action_pagomovil_set_done(self):
        """Confirm a pending Pago Móvil notification and post-process it."""
        self.ensure_one()
        if self.provider_code != "pagomovil" or self.state != "pending":
            return
        self._set_done()
        self._post_process()

    def action_pagomovil_set_canceled(self):
        """Reject a pending Pago Móvil notification."""
        self.ensure_one()
        if self.provider_code != "pagomovil" or self.state != "pending":
            return
        self._set_canceled()
        self._post_process()

    def _pagomovil_register(
        self, vat, phone, bank_code, bank_reference, receipt_raw, receipt_filename
    ):
        """Store the customer notification and leave the transaction pending."""
        self.ensure_one()
        if self.provider_code != "pagomovil":
            raise ValidationError(_("Esta transacción no es un pago móvil."))
        if self.state == "pending":
            return
        if self.state != "draft":
            raise ValidationError(_("Este pago móvil ya no se puede registrar."))

        vat = normalize_vat(vat)
        phone = normalize_phone(phone)
        bank_code = normalize_bank(bank_code)
        bank_reference = normalize_reference(bank_reference)
        receipt, filename = prepare_receipt(receipt_raw, receipt_filename)
        self._pagomovil_check_duplicate(phone, bank_reference)
        provider = self.provider_id
        self.write(
            {
                "pagomovil_vat": vat,
                "pagomovil_phone": phone,
                "pagomovil_bank": bank_code,
                "pagomovil_reference": bank_reference,
                "pagomovil_receipt": receipt,
                "pagomovil_receipt_filename": filename,
                "pagomovil_destination_holder": provider.pagomovil_holder,
                "pagomovil_destination_vat": provider.pagomovil_vat,
                "pagomovil_destination_phone": provider.pagomovil_phone,
                "pagomovil_destination_bank": provider.pagomovil_bank,
            }
        )
        self._handle_notification_data("pagomovil", {"reference": self.reference})

    def _pagomovil_check_duplicate(self, phone, bank_reference):
        duplicate = self.sudo().search(
            [
                ("id", "!=", self.id),
                ("provider_id.code", "=", "pagomovil"),
                ("company_id", "=", self.company_id.id),
                ("pagomovil_phone", "=", phone),
                ("pagomovil_reference", "=", bank_reference),
                ("state", "not in", ("cancel", "error")),
            ],
            limit=1,
        )
        if duplicate:
            raise ValidationError(
                _(
                    "Ya existe un pago móvil con el teléfono %(phone)s "
                    "y la referencia %(reference)s (%(tx)s).",
                    phone=phone,
                    reference=bank_reference,
                    tx=duplicate.reference,
                )
            )

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != "pagomovil" or len(tx) == 1:
            return tx
        reference = notification_data.get("reference")
        tx = self.search(
            [("reference", "=", reference), ("provider_id.code", "=", "pagomovil")]
        )
        if not tx:
            raise ValidationError(
                _("No se encontró un pago móvil con la referencia %s.", reference)
            )
        return tx

    def _process_notification_data(self, notification_data):
        super()._process_notification_data(notification_data)
        if self.provider_code != "pagomovil":
            return
        self.provider_reference = self.pagomovil_reference
        self._set_pending()

    def _get_received_message(self):
        message = super()._get_received_message()
        if self.provider_code != "pagomovil" or self.state != "pending":
            return message
        return _(
            "Pago móvil %(ref)s por %(amount)s está pendiente. "
            "RIF o cédula %(vat)s, teléfono %(phone)s, banco %(bank)s, "
            "referencia %(bank_ref)s.",
            ref=self.reference,
            amount=format_amount(self.env, self.amount, self.currency_id),
            vat=self.pagomovil_vat,
            phone=self.pagomovil_phone,
            bank=dict(PAGOMOVIL_BANKS).get(self.pagomovil_bank, ""),
            bank_ref=self.pagomovil_reference,
        )
