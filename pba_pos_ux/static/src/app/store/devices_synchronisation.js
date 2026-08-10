/** @odoo-module **/

import DevicesSynchronisation from "@point_of_sale/app/store/devices_synchronisation";
import { patch } from "@web/core/utils/patch";

const PBA_OWNED_ORDER_SYNC_FIELDS = new Set([
    "id",
    "write_date",
    "state",
    "pba_lock_device_token",
    "pba_lock_owner_name",
    "pba_lock_owner_user_id",
    "pba_lock_owner_employee_id",
    "pba_lock_expire",
]);

patch(DevicesSynchronisation.prototype, {
    _pbaOrderIdFromSyncVals(vals) {
        const raw =
            vals?.order_id?.id ||
            vals?.order_id ||
            vals?.pos_order_id?.id ||
            vals?.pos_order_id;
        return typeof raw === "number" ? raw : false;
    },

    _pbaSanitizeSyncRecords(recordsByModel) {
        if (!recordsByModel?.["pos.order"]?.length) {
            return recordsByModel;
        }
        const deviceToken = this.pos.pbaEnsureDeviceToken?.();
        if (!deviceToken) {
            return recordsByModel;
        }

        const protectedOrderIds = new Set();
        const sanitizedOrders = recordsByModel["pos.order"].map((vals) => {
            const local = this.models["pos.order"]?.get(vals.id);
            if (
                !local ||
                local.pba_lock_device_token !== deviceToken ||
                !this.pos.pbaIsOrderLockActive?.(local)
            ) {
                return vals;
            }
            protectedOrderIds.add(vals.id);
            const partial = {};
            for (const field of PBA_OWNED_ORDER_SYNC_FIELDS) {
                if (field in vals) {
                    partial[field] = vals[field];
                }
            }
            return partial;
        });

        if (!protectedOrderIds.size) {
            return recordsByModel;
        }

        const result = { ...recordsByModel, "pos.order": sanitizedOrders };
        for (const model of ["pos.order.line", "pos.payment", "pos.pack.operation.lot"]) {
            if (!result[model]?.length) {
                continue;
            }
            result[model] = result[model].filter(
                (vals) => !protectedOrderIds.has(this._pbaOrderIdFromSyncVals(vals))
            );
        }
        return result;
    },

    processStaticRecords(staticRecords) {
        return super.processStaticRecords(this._pbaSanitizeSyncRecords(staticRecords));
    },

    processDynamicRecords(dynamicRecords) {
        const result = super.processDynamicRecords(
            this._pbaSanitizeSyncRecords(dynamicRecords)
        );
        this.pos.pbaReclaimActiveSharedOrderSession?.();
        return result;
    },
});
