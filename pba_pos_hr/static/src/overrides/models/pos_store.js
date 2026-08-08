/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/store/pos_store";

patch(PosStore.prototype, {
    get pbaPosHrIsBasicCashier() {
        if (!this.config.module_pos_hr) {
            return false;
        }
        const cashier = this.get_cashier();
        return Boolean(cashier && cashier._role !== "manager");
    },

    showScreen(name, props) {
        if (name === "PaymentScreen" && this.pbaPosHrIsBasicCashier) {
            return;
        }
        return super.showScreen(...arguments);
    },

    async pay() {
        if (this.pbaPosHrIsBasicCashier) {
            return;
        }
        return await super.pay(...arguments);
    },
});
