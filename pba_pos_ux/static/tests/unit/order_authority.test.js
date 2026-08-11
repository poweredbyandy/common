import { describe, expect, test } from "@odoo/hoot";
import {
    filterIndexedDbPosData,
    isLocalPosOrder,
    shouldPersistPosOrderLocally,
} from "@pba_pos_ux/utils/order_authority";
import { getOrCreateDeviceToken, PBA_DEVICE_TOKEN_KEY } from "@pba_pos_ux/utils/order_lock";

describe("pba_pos_ux order authority", () => {
    test("keeps only local draft orders in IndexedDB", () => {
        expect(isLocalPosOrder({ id: "local-1" })).toBe(true);
        expect(isLocalPosOrder({ id: 12 })).toBe(false);
        expect(shouldPersistPosOrderLocally({ id: "local-1", state: "draft" })).toBe(
            true
        );
        expect(
            shouldPersistPosOrderLocally({ id: 12, state: "draft", finalized: false })
        ).toBe(false);
        expect(
            shouldPersistPosOrderLocally({
                id: "local-1",
                state: "cancel",
                finalized: false,
            })
        ).toBe(false);
    });

    test("filters server orders out of IndexedDB payloads", () => {
        const filtered = filterIndexedDbPosData({
            "pos.order": [
                { id: "local-1", uuid: "u-local" },
                { id: 99, uuid: "u-server" },
            ],
            "pos.order.line": [
                { id: "line-local", order_id: "local-1" },
                { id: 7, order_id: 99 },
            ],
            "pos.payment": [
                { id: "pay-local", pos_order_id: "local-1" },
                { id: 8, pos_order_id: 99 },
            ],
        });
        expect(filtered["pos.order"]).toEqual([{ id: "local-1", uuid: "u-local" }]);
        expect(filtered["pos.order.line"]).toEqual([
            { id: "line-local", order_id: "local-1" },
        ]);
        expect(filtered["pos.payment"]).toEqual([
            { id: "pay-local", pos_order_id: "local-1" },
        ]);
    });

    test("creates an independent device token per session storage", () => {
        const storageA = {
            data: {},
            getItem(key) {
                return this.data[key] || null;
            },
            setItem(key, value) {
                this.data[key] = value;
            },
        };
        const storageB = {
            data: {},
            getItem(key) {
                return this.data[key] || null;
            },
            setItem(key, value) {
                this.data[key] = value;
            },
        };
        const tokenA = getOrCreateDeviceToken(storageA);
        const tokenB = getOrCreateDeviceToken(storageB);
        expect(tokenA).toMatch(/./);
        expect(tokenB).toMatch(/./);
        expect(tokenA).not.toBe(tokenB);
        expect(storageA.getItem(PBA_DEVICE_TOKEN_KEY)).toBe(tokenA);
        expect(storageB.getItem(PBA_DEVICE_TOKEN_KEY)).toBe(tokenB);
        expect(getOrCreateDeviceToken(storageA)).toBe(tokenA);
    });
});
