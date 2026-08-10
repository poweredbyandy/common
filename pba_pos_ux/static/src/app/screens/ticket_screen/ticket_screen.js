/** @odoo-module **/

import { TicketScreen } from "@point_of_sale/app/screens/ticket_screen/ticket_screen";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
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
            this.pos.pbaClaimTrustedDraftOrders();
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

    pbaRefundAllLines() {
        const order = this.getSelectedOrder();
        if (!order) {
            return;
        }
        let refundedSomething = false;
        for (const line of order.get_orderlines()) {
            const toRefundDetail = this.getToRefundDetail(line);
            if (toRefundDetail.destination_order_uuid) {
                continue;
            }
            const refundableQty = line.qty - (line.refunded_qty || 0);
            if (refundableQty <= 0) {
                continue;
            }
            toRefundDetail.qty = refundableQty;
            refundedSomething = true;
        }
        if (!refundedSomething) {
            this.dialog.add(AlertDialog, {
                title: _t("Nothing to refund"),
                body: _t("There are no remaining quantities to refund on this order."),
            });
        }
    },

    async onDoRefund() {
        const order = this.getSelectedOrder();
        if (
            order &&
            !this.getHasItemsToRefund() &&
            !this._doesOrderHaveSoleItem(order)
        ) {
            this.dialog.add(AlertDialog, {
                title: _t("Nothing to refund"),
                body: _t(
                    "Set the quantity to refund on each line, or tap Refund All."
                ),
            });
            return;
        }
        return await super.onDoRefund(...arguments);
    },

    async pbaSyncOrderLocks({ includeOrders = false } = {}) {
        if (this._pbaLockSyncBusy || this.pos.data?.network?.offline) {
            return;
        }
        this._pbaLockSyncBusy = true;
        const showLoader = includeOrders;
        if (showLoader) {
            this.ui.block({ message: _t("Loading orders...") });
        }
        try {
            if (includeOrders) {
                try {
                    await this.pos.data?.deviceSync?.readDataFromServer?.();
                } catch (_error) {
                    // Keep showing local orders if sync is unavailable.
                }
                this.pos.pbaClaimTrustedDraftOrders();
            }
            const openOrders = (this.pos.models["pos.order"] || []).filter(
                (order) => !order.finalized && typeof order.id === "number"
            );
            await this.pos.pbaRefreshOrderLocks(openOrders);
        } finally {
            if (showLoader) {
                this.ui.unblock();
            }
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
