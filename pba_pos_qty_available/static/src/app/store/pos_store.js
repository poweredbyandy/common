/** @odoo-module **/

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";
import { reactive } from "@odoo/owl";
import { debounce } from "@web/core/utils/timing";
import {
    applyFreeQtyMap,
    applyOrderFreeQtyDecrement,
    getProductFreeQty,
    shouldAcceptFreeQtyNotify,
} from "@pba_pos_qty_available/app/utils/free_qty";

const FREE_QTY_RPC_CHUNK = 200;

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.productFreeQty = reactive({});
        this._pendingFreeQtyProductIds = new Set();
        this._freeQtyAppliedOrders = new Set();
        this._freeQtyRefreshInFlight = false;
        this._flushPendingFreeQtyDebounced = debounce(() => {
            const productIds = [...this._pendingFreeQtyProductIds];
            this._pendingFreeQtyProductIds.clear();
            if (productIds.length) {
                this.refreshProductFreeQty(productIds);
            }
        }, 400);
        if (this.config.show_product_qty_available) {
            this.data.connectWebSocket(
                "PRODUCT_FREE_QTY",
                this._onProductFreeQtyNotify.bind(this)
            );
            this._hydrateProductFreeQtyFromLocal();
            window.addEventListener("online", () => {
                this._hydrateProductFreeQtyFromLocal();
            });
        }
    },

    async getProductInfo(product, quantity, priceExtra = 0) {
        const result = await super.getProductInfo(...arguments);
        if (this.config?.show_product_qty_available && product?.is_storable) {
            await this.refreshProductFreeQty([product.id]);
        }
        return result;
    },

    applyOrderFreeQtyDecrement(order, revert = false) {
        const lines = (order?.get_orderlines?.() || []).map((line) => ({
            product: line.product_id,
            qty: line.get_quantity(),
        }));
        const result = applyOrderFreeQtyDecrement({
            productFreeQty: this.productFreeQty,
            appliedOrders: this._freeQtyAppliedOrders,
            order: order ? { uuid: order.uuid, lines } : null,
            revert,
            enabled: Boolean(this.config?.show_product_qty_available),
        });
        for (const [productId, qty] of Object.entries(result.productFreeQty)) {
            const id = parseInt(productId, 10);
            this.productFreeQty[id] = qty;
            const product = this.models["product.product"].get(id);
            if (product) {
                product.update({ free_qty: qty }, { silent: true });
            }
        }
        this._freeQtyAppliedOrders = result.appliedOrders;
    },

    _onProductFreeQtyNotify(payload) {
        if (!this.config?.show_product_qty_available) {
            return;
        }
        if (!shouldAcceptFreeQtyNotify(payload, this.config.warehouse_id?.id)) {
            return;
        }
        const qtyByProduct = payload?.qty_by_product || {};
        if (Object.keys(qtyByProduct).length > 0) {
            this._applyFreeQtyMap(qtyByProduct);
            return;
        }
        if (this.data.network.offline) {
            return;
        }
        const productIds = payload?.product_ids || [];
        if (!productIds.length) {
            return;
        }
        for (const productId of productIds) {
            this._pendingFreeQtyProductIds.add(productId);
        }
        this._flushPendingFreeQtyDebounced();
    },

    _applyFreeQtyMap(qtyByProduct) {
        const productsById = {};
        for (const productId of Object.keys(qtyByProduct || {})) {
            const id = parseInt(productId, 10);
            const product = this.models["product.product"].get(id);
            if (product) {
                productsById[id] = product;
            }
        }
        const next = applyFreeQtyMap(this.productFreeQty, qtyByProduct, productsById);
        for (const [productId, freeQty] of Object.entries(next)) {
            const id = parseInt(productId, 10);
            this.productFreeQty[id] = freeQty;
            const product = this.models["product.product"].get(id);
            if (product) {
                product.update({ free_qty: freeQty }, { silent: true });
            }
        }
    },

    _hydrateProductFreeQtyFromLocal() {
        const products = this.models["product.product"].filter((product) => product.is_storable);
        for (const product of products) {
            if (product.free_qty !== undefined && product.free_qty !== null) {
                this.productFreeQty[product.id] = product.free_qty;
            }
        }
    },

    getProductFreeQty(product) {
        return getProductFreeQty(product, this.productFreeQty);
    },

    async refreshProductFreeQty(productIds = null) {
        if (
            !this.config?.show_product_qty_available ||
            this.data.network.offline ||
            this._freeQtyRefreshInFlight
        ) {
            return;
        }
        if (!productIds?.length) {
            return;
        }
        const products = productIds
            .map((productId) => this.models["product.product"].get(productId))
            .filter((product) => product?.is_storable);
        if (!products.length) {
            return;
        }
        this._freeQtyRefreshInFlight = true;
        try {
            const ids = products.map((product) => product.id);
            for (let index = 0; index < ids.length; index += FREE_QTY_RPC_CHUNK) {
                const chunk = ids.slice(index, index + FREE_QTY_RPC_CHUNK);
                const qtyMap = await this.data.silentCall(
                    "product.product",
                    "get_pos_free_qty",
                    [chunk, this.config.id]
                );
                if (qtyMap) {
                    this._applyFreeQtyMap(qtyMap);
                }
            }
        } finally {
            this._freeQtyRefreshInFlight = false;
        }
    },
});
