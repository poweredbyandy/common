/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import paymentForm from "@payment/js/payment_form";

const MAX_RECEIPT_BYTES = 5 * 1024 * 1024;

paymentForm.include({

    /**
     * @override
     */
    async _prepareInlineForm(providerId, providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode !== "pagomovil") {
            return this._super(...arguments);
        }
        if (flow === "token") {
            return;
        }
        this._setPaymentFlow("direct");
    },

    /**
     * @override
     */
    async _initiatePaymentFlow(providerCode, paymentOptionId, paymentMethodCode, flow) {
        if (providerCode === "pagomovil" && !this._validatePagomovilForm()) {
            this._enableButton();
            return;
        }
        return this._super(...arguments);
    },

    /**
     * @override
     */
    async _processDirectFlow(providerCode, paymentOptionId, paymentMethodCode, processingValues) {
        if (providerCode !== "pagomovil") {
            return this._super(...arguments);
        }
        const form = this._getPagomovilInlineForm();
        const body = new FormData();
        body.append("reference", processingValues.reference);
        body.append("csrf_token", odoo.csrf_token);
        body.append("pagomovil_vat", form.querySelector('[name="pagomovil_vat"]').value);
        body.append("pagomovil_phone", form.querySelector('[name="pagomovil_phone"]').value);
        body.append("pagomovil_bank", form.querySelector('[name="pagomovil_bank"]').value);
        body.append(
            "pagomovil_reference",
            form.querySelector('[name="pagomovil_reference"]').value
        );
        body.append(
            "pagomovil_receipt",
            form.querySelector('[name="pagomovil_receipt"]').files[0]
        );
        try {
            const response = await fetch("/payment/pagomovil/process", {
                method: "POST",
                body,
            });
            const payload = await response.json().catch(() => ({}));
            if (!response.ok) {
                this._displayErrorDialog(
                    _t("No se pudo registrar el pago móvil"),
                    payload.error || _t("Vuelva a intentarlo.")
                );
                this._enableButton();
                return;
            }
            window.location = "/payment/status";
        } catch {
            this._displayErrorDialog(
                _t("No se pudo registrar el pago móvil"),
                _t("Vuelva a intentarlo.")
            );
            this._enableButton();
        }
    },

    _validatePagomovilForm() {
        const form = this._getPagomovilInlineForm();
        if (!form) {
            this._displayErrorDialog(
                _t("No se pudo registrar el pago móvil"),
                _t("Seleccione pago móvil e indique los datos del pago.")
            );
            return false;
        }
        const vat = form.querySelector('[name="pagomovil_vat"]').value.trim();
        const phone = form.querySelector('[name="pagomovil_phone"]').value.trim();
        const bank = form.querySelector('[name="pagomovil_bank"]').value;
        const reference = form.querySelector('[name="pagomovil_reference"]').value.trim();
        const file = form.querySelector('[name="pagomovil_receipt"]').files[0];
        let message = "";
        if (!vat) {
            message = _t("Indique el RIF o la cédula de quien envía el pago.");
        } else if (!phone) {
            message = _t("Indique el teléfono desde el que envió el pago.");
        } else if (!bank) {
            message = _t("Seleccione el banco desde el que envió el pago.");
        } else if (!reference) {
            message = _t("Indique la referencia del pago.");
        } else if (!file) {
            message = _t("Adjunte el comprobante del pago.");
        } else if (file.size > MAX_RECEIPT_BYTES) {
            message = _t("El comprobante supera el tamaño máximo de 5 MB.");
        }
        if (message) {
            this._displayErrorDialog(_t("No se pudo registrar el pago móvil"), message);
            return false;
        }
        return true;
    },

    _getPagomovilInlineForm() {
        const radio = this.el.querySelector('input[name="o_payment_radio"]:checked');
        return radio ? this._getInlineForm(radio) : null;
    },

});
