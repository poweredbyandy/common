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

    _pbaIsEWalletGiftCardLine(orderline) {
        if (!orderline?.product_id) {
            return false;
        }
        const programs = this.pos.models?.["loyalty.program"];
        if (!programs || typeof programs.some !== "function") {
            return false;
        }
        const productId = orderline.product_id.id;
        return programs.some((program) => {
            if (!["gift_card", "ewallet"].includes(program.program_type)) {
                return false;
            }
            const triggers = program.trigger_product_ids;
            if (!triggers || typeof triggers.map !== "function") {
                return false;
            }
            return triggers.map((product) => product.id).includes(productId);
        });
    },

    _pbaEnsureRefundLineRelations(line) {
        if (!line) {
            return false;
        }
        if (!Array.isArray(line.tax_ids)) {
            line.tax_ids = [];
        }
        if (!Array.isArray(line.pack_lot_ids)) {
            line.pack_lot_ids = [];
        }
        if (!Array.isArray(line.combo_line_ids)) {
            line.combo_line_ids = [];
        }
        return Boolean(line.product_id);
    },

    _pbaSanitizeRefundDetails(order) {
        if (!order?.uiState?.lineToRefund) {
            return;
        }
        for (const detail of Object.values(order.uiState.lineToRefund)) {
            const line = detail.line;
            if (!detail.qty) {
                continue;
            }
            if (
                !this._pbaEnsureRefundLineRelations(line) ||
                this._pbaIsEWalletGiftCardLine(line)
            ) {
                detail.qty = 0;
            }
        }
    },

    pbaRefundAllLines() {
        const order = this.getSelectedOrder();
        if (!order) {
            return;
        }
        this.numberBuffer?.reset?.();
        let refundedSomething = false;
        let skippedEwallet = false;
        for (const line of order.get_orderlines()) {
            if (!this._pbaEnsureRefundLineRelations(line)) {
                continue;
            }
            if (this._pbaIsEWalletGiftCardLine(line)) {
                skippedEwallet = true;
                continue;
            }
            const toRefundDetail = this.getToRefundDetail(line);
            if (
                toRefundDetail.destination_order_uuid ||
                toRefundDetail.destination_order
            ) {
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
                body: skippedEwallet
                    ? _t(
                          "Refunding a top up or reward product for an eWallet or gift card program is not allowed."
                      )
                    : _t(
                          "There are no remaining quantities to refund on this order."
                      ),
            });
        }
    },

    async onDoRefund() {
        const order = this.getSelectedOrder();
        this._pbaSanitizeRefundDetails(order);
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
