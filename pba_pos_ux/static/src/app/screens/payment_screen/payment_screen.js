/** @odoo-module **/

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        if (this.currentOrder && !this.currentOrder.finalized) {
            this.currentOrder.set_to_invoice(true);
        }
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
});
