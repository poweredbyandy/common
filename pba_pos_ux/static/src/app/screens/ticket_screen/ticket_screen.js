/** @odoo-module **/

import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { patch } from "@web/core/utils/patch";
import { onMounted, onWillStart, onWillUnmount } from "@odoo/owl";
import { PBA_LOCK_HEARTBEAT_MS } from "@pba_pos_ux/utils/order_lock";

patch(TicketScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this._pbaLockSyncTimer = null;
        this._pbaLockSyncBusy = false;
        onWillStart(async () => {
            await this.pbaSyncOrderLocks({ includeOrders: true });
        });
        onMounted(() => {
            this._pbaLockSyncTimer = setInterval(() => {
                this.pbaSyncOrderLocks({ includeOrders: false });
            }, PBA_LOCK_HEARTBEAT_MS);
        });
        onWillUnmount(() => {
            if (this._pbaLockSyncTimer) {
                clearInterval(this._pbaLockSyncTimer);
                this._pbaLockSyncTimer = null;
            }
        });
    },

    async pbaSyncOrderLocks({ includeOrders = false } = {}) {
        if (this._pbaLockSyncBusy || this.pos.data?.network?.offline) {
            return;
        }
        this._pbaLockSyncBusy = true;
        try {
            if (includeOrders) {
                try {
                    await this.pos.data?.deviceSync?.readDataFromServer?.();
                } catch (_error) {
                    // Keep showing local orders if sync is unavailable.
                }
            }
            const openOrders = (this.pos.models["pos.order"] || []).filter(
                (order) => !order.finalized && typeof order.id === "number"
            );
            await this.pos.pbaRefreshOrderLocks(openOrders);
        } finally {
            this._pbaLockSyncBusy = false;
        }
    },

    isOrderLockedByOther(order) {
        return this.pos.pbaIsOrderLockedByOther(order);
    },

    isOrderOccupied(order) {
        return this.pos.pbaIsOrderOccupied(order);
    },

    getOrderLockLabel(order) {
        return this.pos.pbaGetOrderLockLabel(order);
    },

    getOrderLockAvatar(order) {
        return this.pos.pbaGetOrderLockAvatar(order);
    },

    onOrderLockAvatarImgError(ev) {
        ev.target.classList.add("d-none");
    },

    shouldHideDeleteButton(order) {
        return (
            super.shouldHideDeleteButton(...arguments) || this.isOrderOccupied(order)
        );
    },

    async onClickOrder(clickedOrder) {
        if (clickedOrder && !clickedOrder.finalized) {
            this.setSelectedOrder(clickedOrder);
            this.numberBuffer.reset();
            await this._setOrder(clickedOrder);
            return;
        }
        return super.onClickOrder(...arguments);
    },

    async _setOrder(order) {
        if (!order) {
            return;
        }
        if (order.finalized) {
            this.pos.pbaShowProcessedOrderAlert();
            return;
        }
        const opened = await this.pos.pbaOpenOrder(order);
        if (!opened) {
            return;
        }
        this.pos.ticket_screen_mobile_pane = "left";
        const screenData = order.get_screen_data();
        const screenName =
            screenData?.name && screenData.name !== "TicketScreen"
                ? screenData.name
                : "ProductScreen";
        const props = {};
        if (screenName === "PaymentScreen") {
            props.orderUuid = order.uuid;
        }
        this.pos.showScreen(screenName, props);
    },
});
