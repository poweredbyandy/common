/** @odoo-module **/

import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { PosStore } from "@point_of_sale/app/store/pos_store";
import { makeAwaitable } from "@point_of_sale/app/store/make_awaitable_dialog";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import {
    countPendingPosOrders,
    getOrCreateDeviceToken,
    getPosOrderLockOwnerAvatar,
    getPosOrderLockOwnerName,
    isPosOrderLockActive,
    isPosOrderLockedByOther,
    isPosOrderOccupied,
    isSharedPosOrder,
    PBA_LOCK_HEARTBEAT_MS,
} from "@pba_pos_ux/utils/order_lock";

const PRODUCT_LIST_VIEW_KEY = "pba_pos_ux_product_list_view";
const SHOW_NUMPAD_KEY = "pba_pos_ux_show_numpad";

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

function readSavedShowNumpad() {
    const candidates = [
        window.sessionStorage.getItem(SHOW_NUMPAD_KEY),
        window.localStorage.getItem(SHOW_NUMPAD_KEY),
    ];
    for (const value of candidates) {
        if (value === "1" || value === "true") {
            return true;
        }
        if (value === "0" || value === "false") {
            return false;
        }
    }
    return false;
}

function persistShowNumpad(show) {
    const value = show ? "1" : "0";
    window.sessionStorage.setItem(SHOW_NUMPAD_KEY, value);
    window.localStorage.setItem(SHOW_NUMPAD_KEY, value);
}

patch(PosStore.prototype, {
    async setup() {
        // Token must exist before super.setup(): afterProcessServerData acquires locks there.
        this.pbaDeviceToken = getOrCreateDeviceToken();
        this._pbaLockHeartbeat = null;
        this._pbaLockedOrderServerId = null;
        this._pbaLockBusy = false;
        await super.setup(...arguments);
        this.productListView = readSavedProductListView();
        this.showNumpad = readSavedShowNumpad();
    },

    toggleShowNumpad() {
        this.setShowNumpad(!this.showNumpad);
    },

    setShowNumpad(show) {
        const next = Boolean(show);
        if (this.showNumpad === next) {
            return;
        }
        persistShowNumpad(next);
        this.showNumpad = next;
    },

    pbaEnsureDeviceToken() {
        if (!this.pbaDeviceToken) {
            this.pbaDeviceToken = getOrCreateDeviceToken();
        }
        return this.pbaDeviceToken;
    },

    async _pbaWithUiBlock(message, callback) {
        this.ui.block({ message });
        try {
            return await callback();
        } finally {
            this.ui.unblock();
        }
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

    get pbaPendingOrderCount() {
        const { orderToCreate, orderToUpdate } = this.getPendingOrder();
        return countPendingPosOrders({
            orderToCreate,
            orderToUpdate,
            unsyncData: this.data?.network?.unsyncData || [],
        });
    },

    get firstScreen() {
        const screen = super.firstScreen;
        if (screen === "ProductScreen") {
            return "TicketScreen";
        }
        return screen;
    },

    showScreen(name, props) {
        if (
            name === "ProductScreen" &&
            this.mainScreen?.component?.name === "LoginScreen" &&
            !props?.orderUuid
        ) {
            name = "TicketScreen";
        }
        if (
            name === "TicketScreen" &&
            this.get_order() &&
            this.mainScreen?.component &&
            !this._pbaSkipLeaveOnTicketScreen
        ) {
            this.pbaShowOrdersList(props);
            return true;
        }
        return super.showScreen(name, props);
    },

    async pbaShowOrdersList(props = {}) {
        if (this._pbaLockBusy) {
            return false;
        }
        this._pbaLockBusy = true;
        try {
            if (this.get_order() && !(await this.pbaPersistAndReleaseCurrentOrder())) {
                return false;
            }
            return await this._pbaWithUiBlock(_t("Loading orders..."), async () => {
                this._pbaSkipLeaveOnTicketScreen = true;
                try {
                    super.showScreen("TicketScreen", props);
                } finally {
                    this._pbaSkipLeaveOnTicketScreen = false;
                }
                this.pbaClearActiveOrder();
                return true;
            });
        } finally {
            this._pbaLockBusy = false;
        }
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

    add_new_order(data = {}) {
        const order = super.add_new_order({ ...data, to_invoice: true });
        if (order && !order.is_to_invoice()) {
            order.set_to_invoice(true);
        }
        return order;
    },

    afterOrderDeletion() {
        const openOrders = this.get_open_orders();
        if (openOrders.length) {
            this.set_order(openOrders.at(-1));
            return;
        }
        this._pbaStopLockHeartbeat();
        this.set_order(null);
    },

    set_order(order, options) {
        super.set_order(...arguments);
        if (order && !order.finalized && !order.is_to_invoice()) {
            order.set_to_invoice(true);
        }
    },

    selectEmptyOrder() {
        this.pbaClearActiveOrder();
    },

    selectNextOrder() {
        const orders = this.models["pos.order"].filter((order) => !order.finalized);
        this.set_order(orders[0] || null);
    },

    async addLineToCurrentOrder(vals, opts = {}, configure = true) {
        if (!this.get_order()) {
            this.add_new_order();
        }
        return await super.addLineToCurrentOrder(...arguments);
    },

    pbaGetTrustedConfigIds() {
        return new Set([
            this.config.id,
            ...(this.config.raw?.trusted_config_ids || []),
        ]);
    },

    pbaClaimOrderToCurrentSession(order) {
        if (!order || order.finalized || order.state === "cancel") {
            return false;
        }
        if (!this.session || !this.config) {
            return false;
        }
        const configId = order.config_id?.id;
        const trustedIds = this.pbaGetTrustedConfigIds();
        if (configId && !trustedIds.has(configId)) {
            return false;
        }
        if (
            order.session_id?.id === this.session.id &&
            order.config_id?.id === this.config.id
        ) {
            return false;
        }
        order.update({
            config_id: this.config,
            session_id: this.session,
        });
        return true;
    },

    pbaClaimTrustedDraftOrders(orders) {
        const draftOrders =
            orders ||
            (this.models["pos.order"] || []).filter(
                (order) => order.state === "draft" && !order.finalized
            );
        let claimed = false;
        for (const order of draftOrders) {
            if (this.pbaClaimOrderToCurrentSession(order)) {
                claimed = true;
            }
        }
        return claimed;
    },

    pbaReclaimActiveSharedOrderSession() {
        const order = this.get_order();
        if (!order || order.finalized) {
            return false;
        }
        return this.pbaClaimOrderToCurrentSession(order);
    },

    async pay() {
        const currentOrder = this.get_order();
        if (!currentOrder) {
            return;
        }
        if (!currentOrder.finalized) {
            currentOrder.set_to_invoice(true);
        }
        this.pbaClaimOrderToCurrentSession(currentOrder);
        if (!(await this.pbaEnsureCustomerForSave(currentOrder))) {
            return;
        }
        if (!(await this._pbaSyncCurrentOrder(currentOrder))) {
            this.pbaShowSaveFailedAlert();
            return;
        }
        return await super.pay(...arguments);
    },

    async selectPartner() {
        if (!this.get_order()) {
            await this.pbaAddNewOrder();
        }
        if (!this.get_order()) {
            return false;
        }
        const result = await super.selectPartner(...arguments);
        const order = this.get_order();
        if (order && !order.finalized) {
            await this._pbaSyncCurrentOrder(order);
        }
        return result;
    },

    getSyncAllOrdersContext(orders, options = {}) {
        return {
            ...super.getSyncAllOrdersContext(orders, options),
            pba_device_token: this.pbaEnsureDeviceToken(),
        };
    },

    pbaGetNoOrderStub() {
        if (!this._pbaNoOrderStub) {
            this._pbaNoOrderStub = {
                state: "draft",
                finalized: false,
                lines: [],
                totalQuantity: 0,
                general_note: "",
                payment_ids: [],
                uiState: {},
                is_empty: () => true,
                get_partner: () => null,
                getSortedOrderlines: () => [],
                get_selected_orderline: () => null,
                get_last_orderline: () => null,
                get_total_with_tax: () => 0,
                is_to_invoice: () => true,
                set_to_invoice: () => undefined,
            };
        }
        return this._pbaNoOrderStub;
    },

    pbaClearActiveOrder({ deleteEmptyLocal = false } = {}) {
        const order = this.get_order();
        if (order) {
            this.pbaReleaseOrderLock(order, { silent: true });
            if (
                deleteEmptyLocal &&
                !isSharedPosOrder(order) &&
                order.is_empty() &&
                !order.get_partner()
            ) {
                this.removeOrder(order, false);
                this.removePendingOrder(order);
            }
        }
        this._pbaStopLockHeartbeat();
        this.set_order(null);
    },

    async afterProcessServerData() {
        await super.afterProcessServerData(...arguments);
        const order = this.get_order();
        if (!order || order.finalized) {
            this.pbaClearActiveOrder();
            return;
        }
        if (!isSharedPosOrder(order) && order.is_empty() && !order.get_partner()) {
            this.pbaClearActiveOrder({ deleteEmptyLocal: true });
            return;
        }
        const acquired = await this.pbaAcquireOrderLock(order, { silent: true });
        if (!acquired) {
            this.pbaClearActiveOrder();
        }
    },

    async clickSaveOrder() {
        const order = this.get_order();
        if (!order) {
            return false;
        }
        if (this.pbaIsDisposableEmptyOrder(order)) {
            await this.pbaDiscardEmptyOrder(order);
            this._pbaSkipLeaveOnTicketScreen = true;
            try {
                this.showScreen("TicketScreen");
            } finally {
                this._pbaSkipLeaveOnTicketScreen = false;
            }
            return true;
        }
        if (!(await this.pbaEnsureCustomerForSave(order))) {
            return false;
        }
        if (!(await this.pbaPersistAndReleaseCurrentOrder())) {
            this.pbaShowSaveFailedAlert();
            return false;
        }
        this.notification.add(_t("Order saved for later"), { type: "success" });
        this._pbaSkipLeaveOnTicketScreen = true;
        try {
            this.showScreen("TicketScreen");
            this._pbaStopLockHeartbeat();
            this.set_order(null);
        } finally {
            this._pbaSkipLeaveOnTicketScreen = false;
        }
        return true;
    },

    async showLoginScreen() {
        if (!(await this.pbaPersistAndReleaseCurrentOrder())) {
            return;
        }
        this.pbaClearActiveOrder();
        this.previousScreen = "TicketScreen";
        return await super.showLoginScreen(...arguments);
    },

    async onDeleteOrder(order) {
        if (order && this.pbaIsOrderOccupied(order)) {
            await this.pbaRefreshOrderLocks([order]);
        }
        if (order && this.pbaIsOrderLockedByOther(order)) {
            this.pbaShowLockAlert(getPosOrderLockOwnerName(order));
            return false;
        }
        if (order && this.pbaIsOrderOccupied(order)) {
            this.dialog.add(AlertDialog, {
                title: _t("Order in use"),
                body: _t("Leave the order before deleting it."),
            });
            return false;
        }
        if (order && isSharedPosOrder(order)) {
            await this.pbaReleaseOrderLock(order, { silent: true });
        }
        return await super.onDeleteOrder(...arguments);
    },

    pbaGetLockOwnerName() {
        return this.pbaGetLockOwnerInfo().name;
    },

    _pbaToRpcId(value) {
        if (value == null || value === false) {
            return false;
        }
        if (typeof value === "number") {
            return value;
        }
        if (typeof value === "object") {
            const id = value.id;
            return typeof id === "number" ? id : false;
        }
        const parsed = parseInt(value, 10);
        return Number.isFinite(parsed) ? parsed : false;
    },

    pbaGetLockOwnerInfo() {
        const cashier = this.get_cashier();
        const name = String(cashier?.name || this.user?.name || _t("Cashier"));
        // pos_hr's get_cashier_user_id() returns a res.users record, not an id.
        let userId =
            this._pbaToRpcId(this.get_cashier_user_id?.()) ||
            this._pbaToRpcId(this.user?.id) ||
            false;
        let employeeId = false;
        if (this.config?.module_pos_hr && cashier?.id) {
            employeeId = this._pbaToRpcId(cashier.id);
            if (!userId) {
                userId = this._pbaToRpcId(cashier.user_id);
            }
        }
        return {
            name,
            user_id: userId || false,
            employee_id: employeeId || false,
        };
    },

    pbaIsOrderLockedByOther(order) {
        return isPosOrderLockedByOther(order, this.pbaEnsureDeviceToken());
    },

    pbaIsOrderOccupied(order) {
        return isPosOrderOccupied(order);
    },

    pbaIsOrderLockActive(order) {
        return isPosOrderLockActive(order);
    },

    pbaGetOrderLockLabel(order) {
        const owner = getPosOrderLockOwnerName(order);
        if (!owner || !this.pbaIsOrderLockActive(order)) {
            return "";
        }
        if (!this.pbaIsOrderLockedByOther(order)) {
            return _t("In use by you (%s)", owner);
        }
        return _t("In use by %s", owner);
    },

    _pbaLockRpcContext() {
        return {
            context: { login_number: parseInt(odoo.login_number, 10) || 0 },
        };
    },

    async pbaRefreshOrderLocks(orders = []) {
        const ids = (orders || [])
            .filter((order) => isSharedPosOrder(order) && !order.finalized)
            .map((order) => order.id);
        if (!ids.length || this.data?.network?.offline) {
            return false;
        }
        try {
            const result = await this.data.call(
                "pos.order",
                "pba_get_order_locks",
                [ids],
                this._pbaLockRpcContext()
            );
            this._pbaApplyLockPayload(result, { applyState: true });
            return true;
        } catch (_error) {
            return false;
        }
    },

    pbaGetOrderLockAvatar(order) {
        return getPosOrderLockOwnerAvatar(order);
    },

    pbaShowLockAlert(ownerName) {
        this.dialog.add(AlertDialog, {
            title: _t("Order in use"),
            body: _t("In use by %s", ownerName || _t("another device")),
        });
    },

    pbaShowProcessedOrderAlert() {
        this.dialog.add(AlertDialog, {
            title: _t("Order already processed"),
            body: _t("This order has already been processed and can no longer be opened."),
        });
    },

    pbaShowOfflineSharedOrderAlert() {
        this.dialog.add(AlertDialog, {
            title: _t("Offline"),
            body: _t(
                "Shared orders cannot be opened while offline because their lock cannot be validated."
            ),
        });
    },

    pbaShowSaveFailedAlert() {
        this.dialog.add(AlertDialog, {
            title: _t("Order not saved"),
            body: _t(
                "The order could not be saved on the server. It remains open so you can try again."
            ),
        });
    },

    pbaOrderNeedsCustomer(order) {
        if (!order || order.finalized || order.get_partner()) {
            return false;
        }
        return !order.is_empty() || Boolean(order.payment_ids?.length);
    },

    pbaIsDisposableEmptyOrder(order) {
        return Boolean(
            order &&
                !order.finalized &&
                order.is_empty() &&
                !(order.payment_ids && order.payment_ids.length)
        );
    },

    async pbaDiscardEmptyOrder(order) {
        if (!this.pbaIsDisposableEmptyOrder(order)) {
            return false;
        }
        await this.pbaReleaseOrderLock(order, { silent: true });
        this._pbaStopLockHeartbeat();
        await this.deleteOrders([order]);
        if (this.get_order()?.uuid === order.uuid) {
            this.set_order(null);
        }
        return true;
    },

    async pbaEnsureCustomerForSave(order = this.get_order()) {
        if (!this.pbaOrderNeedsCustomer(order)) {
            return true;
        }
        return await this._rtPosUxRequestCustomer(order);
    },

    async _pbaSyncCurrentOrder(order) {
        this.addPendingOrder([order.id]);
        try {
            const syncedOrders = await this.syncAllOrders({
                orders: [order],
                throw: true,
            });
            return Boolean(
                syncedOrders?.some(
                    (syncedOrder) =>
                        syncedOrder === order ||
                        syncedOrder.id === order.id ||
                        syncedOrder.uuid === order.uuid
                )
            );
        } catch (_error) {
            return false;
        }
    },

    async pbaPersistCurrentOrder() {
        const order = this.get_order();
        if (!order || order.finalized) {
            return true;
        }
        if (this.pbaIsDisposableEmptyOrder(order)) {
            await this.pbaDiscardEmptyOrder(order);
            return true;
        }
        if (!(await this.pbaEnsureCustomerForSave(order))) {
            return false;
        }
        return await this._pbaWithUiBlock(_t("Saving order..."), async () => {
            return await this._pbaSyncCurrentOrder(order);
        });
    },

    async pbaPersistAndReleaseCurrentOrder() {
        const order = this.get_order();
        if (!order || order.finalized) {
            return true;
        }
        if (this.pbaIsDisposableEmptyOrder(order)) {
            await this.pbaDiscardEmptyOrder(order);
            return true;
        }
        if (!(await this.pbaEnsureCustomerForSave(order))) {
            return false;
        }
        return await this._pbaWithUiBlock(_t("Saving order..."), async () => {
            if (!(await this._pbaSyncCurrentOrder(order))) {
                return false;
            }
            await this.pbaReleaseOrderLock(order, { silent: true });
            return true;
        });
    },

    _pbaStopLockHeartbeat() {
        if (this._pbaLockHeartbeat) {
            clearInterval(this._pbaLockHeartbeat);
            this._pbaLockHeartbeat = null;
        }
        this._pbaLockedOrderServerId = null;
    },

    _pbaStartLockHeartbeat(order) {
        this._pbaStopLockHeartbeat();
        if (!isSharedPosOrder(order)) {
            return;
        }
        this._pbaLockedOrderServerId = order.id;
        this._pbaLockHeartbeat = setInterval(() => {
            this.pbaRenewOrderLock().catch(() => undefined);
        }, PBA_LOCK_HEARTBEAT_MS);
    },

    _pbaApplyLockPayload(result, { applyState = false } = {}) {
        if (!result?.order?.length) {
            return;
        }
        for (const vals of result.order) {
            const order = this.models["pos.order"].get(vals.id);
            if (!order) {
                continue;
            }
            const update = {
                pba_lock_device_token: vals.pba_lock_device_token || false,
                pba_lock_owner_name: vals.pba_lock_owner_name || false,
                pba_lock_owner_user_id: vals.pba_lock_owner_user_id || false,
                pba_lock_owner_employee_id: vals.pba_lock_owner_employee_id || false,
                pba_lock_expire: vals.pba_lock_expire || false,
            };
            if (applyState && vals.state) {
                update.state = vals.state;
            }
            const ownershipChanged =
                (order.pba_lock_device_token || false) !== update.pba_lock_device_token ||
                (order.pba_lock_owner_name || false) !== update.pba_lock_owner_name ||
                (order.pba_lock_owner_user_id || false) !==
                    update.pba_lock_owner_user_id ||
                (order.pba_lock_owner_employee_id || false) !==
                    update.pba_lock_owner_employee_id ||
                (applyState && vals.state && order.state !== vals.state);
            if (!ownershipChanged) {
                if ((order.pba_lock_expire || false) !== update.pba_lock_expire) {
                    order.update(
                        { pba_lock_expire: update.pba_lock_expire },
                        { silent: true }
                    );
                }
                continue;
            }
            order.update(update);
        }
    },

    async pbaReleaseOrderLock(order = this.get_order(), options = {}) {
        const silent = Boolean(options.silent);
        if (!order || !isSharedPosOrder(order)) {
            if (this._pbaLockedOrderServerId && (!order || order.id === this._pbaLockedOrderServerId)) {
                this._pbaStopLockHeartbeat();
            }
            return true;
        }
        if (this.data?.network?.offline) {
            this._pbaStopLockHeartbeat();
            return true;
        }
        try {
            const result = await this.data.call(
                "pos.order",
                "pba_release_order_lock",
                [order.id, this.pbaEnsureDeviceToken()],
                this._pbaLockRpcContext()
            );
            this._pbaApplyLockPayload(result);
            if (this._pbaLockedOrderServerId === order.id) {
                this._pbaStopLockHeartbeat();
            }
            return Boolean(result?.success);
        } catch (_error) {
            if (!silent) {
                this.dialog.add(AlertDialog, {
                    title: _t("Error"),
                    body: _t("Could not release the order lock."),
                });
            }
            this._pbaStopLockHeartbeat();
            return false;
        }
    },

    async pbaRenewOrderLock(order = this.get_order()) {
        if (
            !order ||
            !isSharedPosOrder(order) ||
            this.data?.network?.offline ||
            this._pbaLockedOrderServerId !== order.id
        ) {
            return false;
        }
        try {
            const result = await this.data.call(
                "pos.order",
                "pba_renew_order_lock",
                [order.id, this.pbaEnsureDeviceToken()],
                this._pbaLockRpcContext()
            );
            this._pbaApplyLockPayload(result);
            if (!result?.success) {
                this._pbaStopLockHeartbeat();
            }
            return Boolean(result?.success);
        } catch (_error) {
            return false;
        }
    },

    async pbaAcquireOrderLock(order, options = {}) {
        const silent = Boolean(options.silent);
        if (!order) {
            return false;
        }
        if (order.finalized) {
            if (!silent) {
                this.pbaShowProcessedOrderAlert();
            }
            return false;
        }
        if (!isSharedPosOrder(order)) {
            this._pbaStartLockHeartbeat(order);
            return true;
        }
        if (this.data?.network?.offline) {
            if (!silent) {
                this.pbaShowOfflineSharedOrderAlert();
            }
            return false;
        }
        await this.pbaRefreshOrderLocks([order]);
        if (order.finalized) {
            if (!silent) {
                this.pbaShowProcessedOrderAlert();
            }
            return false;
        }
        if (this.pbaIsOrderLockedByOther(order)) {
            if (!silent) {
                this.pbaShowLockAlert(getPosOrderLockOwnerName(order));
            }
            return false;
        }
        try {
            const owner = this.pbaGetLockOwnerInfo();
            const deviceToken = this.pbaEnsureDeviceToken();
            if (!deviceToken) {
                throw new Error(_t("Missing device token."));
            }
            const result = await this.data.call(
                "pos.order",
                "pba_acquire_order_lock",
                [
                    this._pbaToRpcId(order.id),
                    String(deviceToken),
                    String(owner.name || ""),
                    this._pbaToRpcId(owner.user_id),
                    this._pbaToRpcId(owner.employee_id),
                ],
                this._pbaLockRpcContext()
            );
            this._pbaApplyLockPayload(result, { applyState: true });
            if (!result?.success) {
                if (!silent) {
                    if (result?.reason === "processed" || order.finalized) {
                        this.pbaShowProcessedOrderAlert();
                    } else {
                        this.pbaShowLockAlert(result?.owner_name);
                    }
                }
                return false;
            }
            this._pbaStartLockHeartbeat(order);
            return true;
        } catch (error) {
            if (!silent) {
                this.dialog.add(AlertDialog, {
                    title: _t("Error"),
                    body:
                        error?.data?.message ||
                        error?.message ||
                        _t("Could not acquire the order lock."),
                });
            }
            return false;
        }
    },

    async pbaOpenOrder(order, options = {}) {
        if (!order) {
            return false;
        }
        if (order.finalized) {
            this.pbaShowProcessedOrderAlert();
            return false;
        }
        const current = this.get_order();
        if (current?.uuid === order.uuid) {
            this.pbaClaimOrderToCurrentSession(order);
            return true;
        }
        if (this._pbaLockBusy) {
            return false;
        }
        this._pbaLockBusy = true;
        try {
            if (current && !(await this.pbaPersistAndReleaseCurrentOrder())) {
                return false;
            }
            return await this._pbaWithUiBlock(_t("Opening order..."), async () => {
                if (isSharedPosOrder(order)) {
                    await this.pbaRefreshOrderLocks([order]);
                    if (order.finalized) {
                        this.pbaShowProcessedOrderAlert();
                        return false;
                    }
                }
                const acquired = await this.pbaAcquireOrderLock(order);
                if (!acquired) {
                    return false;
                }
                if (order.finalized) {
                    this.pbaShowProcessedOrderAlert();
                    return false;
                }
                this.pbaClaimOrderToCurrentSession(order);
                this.set_order(order, options);
                return true;
            });
        } finally {
            this._pbaLockBusy = false;
        }
    },

    async pbaAddNewOrder(data = {}) {
        if (this._pbaLockBusy) {
            return this.get_order();
        }
        this._pbaLockBusy = true;
        try {
            if (!(await this.pbaPersistAndReleaseCurrentOrder())) {
                return this.get_order();
            }
            return await this._pbaWithUiBlock(_t("Creating order..."), async () => {
                const order = this.add_new_order(data);
                this.addPendingOrder([order.id]);
                try {
                    await this.syncAllOrders({ orders: [order] });
                } catch (_error) {
                    // Local order remains available offline.
                }
                await this.pbaAcquireOrderLock(order, { silent: true });
                return order;
            });
        } finally {
            this._pbaLockBusy = false;
        }
    },

    _rtPosUxCanRequestCustomer() {
        return Boolean(this.cashier) && this.session?.state === "opened";
    },

    async _rtPosUxRequestCustomer(order) {
        if (!order || order.finalized) {
            return false;
        }
        if (order.get_partner()) {
            return true;
        }
        if (
            this._rtPosUxSelectingPartner ||
            !this._rtPosUxCanRequestCustomer() ||
            this.get_order()?.uuid !== order.uuid
        ) {
            return Boolean(order.get_partner());
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
            return Boolean(order.get_partner());
        }
        this._rtPosUxSelectingPartner = true;
        try {
            await this._rtPosUxOpenForcedPartnerList(order);
        } finally {
            this._rtPosUxSelectingPartner = false;
        }
        return Boolean(order.get_partner());
    },

    async closeSession() {
        return await this._pbaWithUiBlock(_t("Preparing closing..."), async () => {
            return await super.closeSession(...arguments);
        });
    },

    async closePos() {
        return await this._pbaWithUiBlock(_t("Closing Point of Sale..."), async () => {
            return await super.closePos(...arguments);
        });
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
