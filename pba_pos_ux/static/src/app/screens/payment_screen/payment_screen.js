/** @odoo-module **/

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { floatIsZero, roundPrecision } from "@web/core/utils/numbers";
import { patch } from "@web/core/utils/patch";
import { useState } from "@odoo/owl";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.pbaPaymentUi = useState({ methodsOpen: false });
        if (this.currentOrder && !this.currentOrder.finalized) {
            this.currentOrder.set_to_invoice(true);
        }
    },

    pbaTogglePaymentMethods() {
        this.pbaPaymentUi.methodsOpen = !this.pbaPaymentUi.methodsOpen;
    },

    toggleIsToInvoice() {
        this.currentOrder.set_to_invoice(true);
    },

    shouldDownloadInvoice() {
        return false;
    },

    async _askForCustomerIfRequired() {
        if (!this.currentOrder.get_partner()) {
            await this.pos._rtPosUxRequestCustomer(this.currentOrder);
            if (!this.currentOrder.get_partner()) {
                return false;
            }
        }
        return await super._askForCustomerIfRequired(...arguments);
    },

    _pbaAlignPaymentToTotal() {
        const order = this.currentOrder;
        if (!order || order.finalized || !order.currency) {
            return;
        }
        const rounding = order.currency.rounding;
        const decimals = order.currency.decimal_places;
        const total = order.get_total_with_tax();
        const paid = order.get_total_paid();
        const diff = roundPrecision(total - paid, rounding);
        // Absorb only a single order-currency rounding unit (e.g. 0.01).
        // Larger gaps are real under/over payments and must stay visible.
        if (floatIsZero(diff, decimals) || Math.abs(diff) > rounding + 1e-9) {
            return;
        }
        const line = [...(order.payment_ids || [])]
            .reverse()
            .find((paymentLine) => paymentLine.is_done() && !paymentLine.is_change);
        if (!line) {
            return;
        }
        const newAmount = roundPrecision(line.get_amount() + diff, rounding);
        // currency_pos overrides set_amount() to treat the value as foreign tender.
        // For a 0.01 order-currency residual we must bump `amount` directly.
        if (line.isForeignCurrencyPayment?.()) {
            line.update({ amount: newAmount });
            return;
        }
        line.set_amount(newAmount);
    },

    async addNewPaymentLine(paymentMethod) {
        const result = await super.addNewPaymentLine(...arguments);
        this.pbaPaymentUi.methodsOpen = false;
        this._pbaAlignPaymentToTotal();
        return result;
    },

    async validateOrder(isForceValidate) {
        // Align before is_paid() checks; otherwise a 0.01 residual blocks validation
        // and _finalizeValidation never runs.
        this._pbaAlignPaymentToTotal();
        return await super.validateOrder(...arguments);
    },

    async _finalizeValidation() {
        this._pbaAlignPaymentToTotal();
        return await super._finalizeValidation(...arguments);
    },

    async afterOrderValidation(...args) {
        const order = this.currentOrder;
        if (order && order.state === "draft") {
            this.dialog.add(AlertDialog, {
                title: _t("Payment not completed"),
                body: _t(
                    "The server could not mark this order as paid. Check the remaining amount and validate again."
                ),
            });
            return;
        }
        if (order) {
            this.pos._pbaStopLockHeartbeat();
            await this.pos.pbaReleaseOrderLock(order, { silent: true });
        }
        await super.afterOrderValidation(...args);
    },
});
