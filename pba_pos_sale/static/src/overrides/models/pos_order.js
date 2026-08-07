/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(PosOrder.prototype, {
    setup(vals) {
        super.setup(...arguments);
        if (!this.lines) {
            this.lines = [];
        }
        if (!this.payment_ids) {
            this.payment_ids = [];
        }
    },

    getSortedOrderlines() {
        if (!this.lines) {
            this.lines = [];
        }
        return super.getSortedOrderlines(...arguments) || [];
    },

    getCustomerDisplayData() {
        if (!this.lines) {
            this.lines = [];
        }
        if (!this.payment_ids) {
            this.payment_ids = [];
        }
        return super.getCustomerDisplayData(...arguments);
    },
});
