/** @odoo-module **/

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    async _finalizeValidation() {
        const order = this.currentOrder;
        const result = await super._finalizeValidation(...arguments);
        if (this.pos.config?.show_product_qty_available && order?.state !== "draft") {
            this.pos.applyOrderFreeQtyDecrement(order, false);
        }
        return result;
    },
});
