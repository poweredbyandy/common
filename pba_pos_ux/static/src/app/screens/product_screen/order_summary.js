/** @odoo-module **/

import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(OrderSummary.prototype, {
    get currentOrder() {
        return this.pos.get_order() || this.pos.pbaGetNoOrderStub();
    },

    get pbaHasActiveOrder() {
        return Boolean(this.pos.get_order());
    },

    get pbaTaxTotals() {
        return this.pos.get_order()?.taxTotals;
    },

    get pbaOrderLines() {
        return this.pos.get_order()?.getSortedOrderlines() || [];
    },

    get pbaNoOrderMessage() {
        return _t("No active order. Press + to create one.");
    },

    get pbaEmptyOrderMessage() {
        return _t("Start adding products");
    },
});
