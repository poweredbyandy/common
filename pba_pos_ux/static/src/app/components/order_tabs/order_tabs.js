/** @odoo-module **/

import { OrderTabs } from "@point_of_sale/app/components/order_tabs/order_tabs";
import { patch } from "@web/core/utils/patch";

patch(OrderTabs.prototype, {
    get canOpenQuotation() {
        return typeof this.pos.pbaOpenQuotationSelector === "function";
    },

    onClickQuotation() {
        this.pos.pbaOpenQuotationSelector?.();
    },

    async openOrdersList() {
        const opened = await this.pos.pbaShowOrdersList();
        if (!opened) {
            return;
        }
        this.dialog.closeAll();
    },

    get orders() {
        const current = this.pos.get_order();
        if (!current || current.finalized || current.table_id) {
            return [];
        }
        return [current];
    },

    async newFloatingOrder() {
        this.pos.selectedTable = null;
        const order = await this.pos.pbaAddNewOrder();
        this.pos.showScreen("ProductScreen");
        this.dialog.closeAll();
        return order;
    },

    async selectFloatingOrder(order) {
        const opened = await this.pos.pbaOpenOrder(order);
        if (!opened) {
            return;
        }
        this.pos.selectedTable = null;
        const previousOrderScreen = order.get_screen_data();

        const props = {};
        if (previousOrderScreen?.name === "PaymentScreen") {
            props.orderUuid = order.uuid;
        }

        this.pos.showScreen(previousOrderScreen?.name || "ProductScreen", props);
        this.dialog.closeAll();
    },
});
