/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";
import { formatCurrency } from "@point_of_sale/app/models/utils/currency";

function emptyTaxTotals() {
    return {
        order_sign: 1,
        order_total: 0,
        order_remaining: 0,
        base_amount_currency: 0,
        cash_rounding_base_amount_currency: 0,
        total_amount_currency: 0,
        tax_amount_currency: 0,
        subtotals: [],
    };
}

patch(PosOrder.prototype, {
    get_orderlines() {
        return this.lines || [];
    },

    is_empty() {
        return !this.lines || this.lines.length === 0;
    },

    getSortedOrderlines() {
        if (!this.lines) {
            return [];
        }
        return super.getSortedOrderlines(...arguments) || [];
    },

    get taxTotals() {
        if (!this.lines || !this.payment_ids) {
            return emptyTaxTotals();
        }
        return super.taxTotals;
    },

    getCustomerDisplayData() {
        if (!this.lines || !this.payment_ids) {
            return {
                lines: [],
                finalized: this.finalized,
                amount: formatCurrency(0, this.currency),
                paymentLines: [],
                change: false,
                generalNote: this.general_note || "",
                qrPaymentData: null,
            };
        }
        return super.getCustomerDisplayData(...arguments);
    },
});
