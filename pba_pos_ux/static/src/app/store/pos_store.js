/** @odoo-module **/

import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { patch } from "@web/core/utils/patch";

const PRODUCT_LIST_VIEW_KEY = "pba_pos_ux_product_list_view";

function readSavedProductListView() {
    const candidates = [
        window.sessionStorage.getItem(PRODUCT_LIST_VIEW_KEY),
        window.localStorage.getItem(PRODUCT_LIST_VIEW_KEY),
        window.localStorage.getItem("productListView"),
    ];
    for (const value of candidates) {
        if (value === "grid" || value === "list") {
            return value;
        }
    }
    return "grid";
}

function persistProductListView(view) {
    window.sessionStorage.setItem(PRODUCT_LIST_VIEW_KEY, view);
    window.localStorage.setItem(PRODUCT_LIST_VIEW_KEY, view);
    window.localStorage.setItem("productListView", view);
}

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.productListView = readSavedProductListView();
    },

    get productListViewMode() {
        const viewMode = this.productListView || "grid";
        const switching = this.productListViewSwitching ? " pba_pos_ux_view_switching" : "";
        if (viewMode === "grid") {
            return `d-grid gap-2${switching}`;
        }
        return `list pba_pos_ux_product_list_mode${switching}`;
    },

    get productViewMode() {
        const viewMode = this.productListView || "grid";
        if (viewMode === "grid") {
            return "flex-column";
        }
        return "flex-row align-items-center pba_pos_ux_product_list_item";
    },

    async setProductListView(view) {
        if (
            !["grid", "list"].includes(view) ||
            this.productListView === view ||
            this.productListViewSwitching
        ) {
            return;
        }
        const listEl = document.querySelector(".rightpane .product-list:not(.category-list)");
        const maxScrollBefore = listEl
            ? Math.max(listEl.scrollHeight - listEl.clientHeight, 0)
            : 0;
        const scrollRatio = listEl && maxScrollBefore
            ? listEl.scrollTop / maxScrollBefore
            : 0;

        this.productListViewSwitching = true;
        await new Promise((resolve) => setTimeout(resolve, 110));

        persistProductListView(view);
        this.productListView = view;

        await new Promise((resolve) => requestAnimationFrame(resolve));
        await new Promise((resolve) => requestAnimationFrame(resolve));

        const nextList = document.querySelector(".rightpane .product-list:not(.category-list)");
        if (nextList) {
            const maxScrollAfter = Math.max(nextList.scrollHeight - nextList.clientHeight, 0);
            nextList.scrollTop = scrollRatio * maxScrollAfter;
        }
        this.productListViewSwitching = false;
    },

    createNewOrder(data = {}) {
        const order = super.createNewOrder({ ...data, to_invoice: true });
        if (!order.is_to_invoice()) {
            order.set_to_invoice(true);
        }
        return order;
    },

    set_cashier(user) {
        super.set_cashier(...arguments);
        if (this._rtPosUxCanRequestCustomer()) {
            this._rtPosUxRequestCustomer(this.get_order());
        }
    },

    add_new_order(data = {}) {
        const order = super.add_new_order({ ...data, to_invoice: true });
        if (order && !order.is_to_invoice()) {
            order.set_to_invoice(true);
        }
        this._rtPosUxRequestCustomer(order);
        return order;
    },

    afterOrderDeletion() {
        super.afterOrderDeletion(...arguments);
        const order = this.get_order();
        if (order && !order.finalized && !order.is_to_invoice()) {
            order.set_to_invoice(true);
        }
        this._rtPosUxRequestCustomer(order);
    },

    set_order(order, options) {
        super.set_order(...arguments);
        if (order && !order.finalized) {
            if (!order.is_to_invoice()) {
                order.set_to_invoice(true);
            }
            this._rtPosUxRequestCustomer(order);
        }
    },

    selectEmptyOrder() {
        super.selectEmptyOrder(...arguments);
        const order = this.get_order();
        if (order && !order.finalized && !order.is_to_invoice()) {
            order.set_to_invoice(true);
        }
        this._rtPosUxRequestCustomer(order);
    },

    async selectPartner() {
        const order = this.get_order();
        const result = await super.selectPartner(...arguments);
        if (order && !order.finalized && !order.get_partner()) {
            await this._rtPosUxRequestCustomer(order);
        }
        return result;
    },

    async addLineToCurrentOrder(vals, opts = {}, configure = true) {
        let order = this.get_order();
        if (!order) {
            order = this.add_new_order();
        }
        if (!order.get_partner()) {
            await this._rtPosUxRequestCustomer(order);
            if (!order.get_partner()) {
                return;
            }
        }
        return await super.addLineToCurrentOrder(...arguments);
    },

    async addLineToOrder(vals, order, opts = {}, configure = true) {
        if (order && !order.get_partner()) {
            await this._rtPosUxRequestCustomer(order);
            if (!order.get_partner()) {
                return;
            }
        }
        return await super.addLineToOrder(...arguments);
    },

    async pay() {
        const currentOrder = this.get_order();
        if (currentOrder && !currentOrder.finalized) {
            currentOrder.set_to_invoice(true);
        }
        if (currentOrder && !currentOrder.get_partner()) {
            await this._rtPosUxRequestCustomer(currentOrder);
            if (!currentOrder.get_partner()) {
                return;
            }
        }
        return await super.pay(...arguments);
    },

    _rtPosUxCanRequestCustomer() {
        return Boolean(this.cashier) && this.session?.state === "opened";
    },

    async _rtPosUxRequestCustomer(order) {
        if (
            !order ||
            order.finalized ||
            order.get_partner() ||
            this._rtPosUxSelectingPartner ||
            !this._rtPosUxCanRequestCustomer()
        ) {
            return;
        }
        await new Promise((resolve) => setTimeout(resolve, 0));
        if (
            !order ||
            order.finalized ||
            order.get_partner() ||
            this._rtPosUxSelectingPartner ||
            !this._rtPosUxCanRequestCustomer() ||
            this.get_order()?.uuid !== order.uuid
        ) {
            return;
        }
        this._rtPosUxSelectingPartner = true;
        try {
            while (
                order &&
                !order.finalized &&
                !order.get_partner() &&
                this._rtPosUxCanRequestCustomer() &&
                this.get_order()?.uuid === order.uuid
            ) {
                await this._rtPosUxOpenForcedPartnerList(order);
            }
        } finally {
            this._rtPosUxSelectingPartner = false;
        }
    },

    async _rtPosUxOpenForcedPartnerList(order) {
        if (order.getHasRefundLines?.() && order.get_partner()) {
            return;
        }
        const payload = await makeAwaitable(this.dialog, PartnerList, {
            partner: order.get_partner(),
            forceCustomer: true,
        });
        if (payload) {
            order.set_partner(payload);
        }
    },
});
