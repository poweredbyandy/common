/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { formatCurrency } from "@point_of_sale/app/models/utils/currency";

patch(PosOrder.prototype, {
    getSortedOrderlines() {
        if (!this.lines) {
            return [];
        }
        return super.getSortedOrderlines(...arguments) || [];
    },

    getCustomerDisplayData() {
        if (!this.lines || !this.payment_ids) {
            return {
                lines: [],
                finalized: this.finalized,
                amount: formatCurrency(this.get_total_with_tax?.() || 0, this.currency),
                paymentLines: [],
                change: false,
                generalNote: this.general_note || "",
                qrPaymentData: null,
            };
        }
        return super.getCustomerDisplayData(...arguments);
    },
});
