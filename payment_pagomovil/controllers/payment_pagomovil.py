import logging

from odoo import _
from odoo.exceptions import ValidationError
from odoo.http import Controller, request, route

from odoo.addons.payment.controllers.post_processing import PaymentPostProcessing
from odoo.addons.payment_pagomovil.const import MAX_RECEIPT_BYTES

_logger = logging.getLogger(__name__)


class PaymentPagomovilController(Controller):
    _process_url = "/payment/pagomovil/process"

    @route(_process_url, type="http", auth="public", methods=["POST"], csrf=True)
    def pagomovil_process(self, **post):
        """Store the Pago Móvil notification of the transaction in session."""
        reference = post.get("reference")
        monitored_tx = PaymentPostProcessing()._get_monitored_transaction()
        if (
            not monitored_tx
            or monitored_tx.reference != reference
            or monitored_tx.provider_code != "pagomovil"
        ):
            return self._pagomovil_error(
                _("La sesión de pago expiró. Vuelva a intentarlo.")
            )
        if monitored_tx.state == "pending":
            return request.make_json_response({"redirect": "/payment/status"})
        if monitored_tx.state != "draft":
            return self._pagomovil_error(_("Este pago móvil ya no se puede registrar."))

        upload = request.httprequest.files.get("pagomovil_receipt")
        raw = upload.read(MAX_RECEIPT_BYTES + 1) if upload else b""
        filename = upload.filename if upload else ""
        _logger.info("Pago Móvil notification for reference %s", reference)
        try:
            monitored_tx.sudo()._pagomovil_register(
                post.get("pagomovil_vat"),
                post.get("pagomovil_phone"),
                post.get("pagomovil_bank"),
                post.get("pagomovil_reference"),
                raw,
                filename,
            )
        except ValidationError as error:
            message = error.args[0] if error.args else _("No se pudo registrar el pago móvil.")
            if monitored_tx.state == "draft":
                monitored_tx.sudo()._set_canceled(state_message=str(message))
            return self._pagomovil_error(message)
        return request.make_json_response({"redirect": "/payment/status"})

    def _pagomovil_error(self, message):
        return request.make_json_response({"error": str(message)}, status=400)
