import { describe, expect, test } from "@odoo/hoot";
import {
    countPendingPosOrders,
    createDeviceToken,
    getPosOrderLockOwnerAvatar,
    getPosOrderLockOwnerAvatarColor,
    getPosOrderLockOwnerAvatarInitial,
    getPosOrderLockOwnerAvatarUrl,
    getPosOrderLockOwnerName,
    isPosOrderLockActive,
    isPosOrderLockedByOther,
    isPosOrderOccupied,
    parsePosLockExpireMs,
    isSharedPosOrder,
} from "@pba_pos_ux/utils/order_lock";

describe("pba_pos_ux order lock helpers", () => {
    test("detects shared and local orders", () => {
        expect(isSharedPosOrder({ id: 12 })).toBe(true);
        expect(isSharedPosOrder({ id: "local-1" })).toBe(false);
        expect(isSharedPosOrder(null)).toBe(false);
    });

    test("detects active lock owned by another device", () => {
        const order = {
            pba_lock_device_token: "device-a",
            pba_lock_owner_name: "Cashier A",
            pba_lock_expire: "2099-01-01 10:00:00",
        };
        expect(isPosOrderLockActive(order)).toBe(true);
        expect(isPosOrderOccupied(order)).toBe(true);
        expect(isPosOrderLockedByOther(order, "device-b")).toBe(true);
        expect(isPosOrderLockedByOther(order, "device-a")).toBe(false);
        expect(getPosOrderLockOwnerName(order)).toBe("Cashier A");
    });

    test("ignores expired locks", () => {
        const order = {
            pba_lock_device_token: "device-a",
            pba_lock_expire: "2000-01-01 10:00:00",
        };
        expect(isPosOrderLockedByOther(order, "device-b")).toBe(false);
    });

    test("parses lock expire as UTC naive datetime", () => {
        const now = Date.parse("2026-08-07T18:00:00Z");
        expect(parsePosLockExpireMs("2026-08-07 18:00:30")).toBe(
            Date.parse("2026-08-07T18:00:30Z")
        );
        const order = {
            pba_lock_device_token: "device-a",
            pba_lock_owner_name: "Cashier A",
            pba_lock_expire: "2026-08-07 18:00:30",
        };
        expect(isPosOrderLockedByOther(order, "device-b", now)).toBe(true);
        expect(
            isPosOrderLockedByOther(order, "device-b", Date.parse("2026-08-07T18:01:00Z"))
        ).toBe(false);
    });

    test("counts pending create/update and unsynced network data", () => {
        expect(
            countPendingPosOrders({
                orderToCreate: [{ id: 1 }],
                orderToUpdate: [{ id: 2 }, { id: 3 }],
                unsyncData: [{}, {}],
            })
        ).toBe(5);
    });

    test("creates a device token", () => {
        expect(createDeviceToken()).toMatch(/./);
    });

    test("builds lock owner avatar url from employee or user", () => {
        expect(
            getPosOrderLockOwnerAvatarUrl({ pba_lock_owner_employee_id: 7 })
        ).toBe("/web/image/hr.employee.public/7/avatar_128");
        expect(getPosOrderLockOwnerAvatarUrl({ pba_lock_owner_user_id: 3 })).toBe(
            "/web/image/res.users/3/avatar_128"
        );
        expect(getPosOrderLockOwnerAvatarUrl({})).toBe("");
    });

    test("builds colored initial avatar fallback from owner name", () => {
        expect(getPosOrderLockOwnerAvatarInitial("andy engit")).toBe("A");
        expect(getPosOrderLockOwnerAvatarInitial("")).toBe("?");
        expect(getPosOrderLockOwnerAvatarColor("Andy", 7)).toMatch(/^hsl\(/);
        const avatar = getPosOrderLockOwnerAvatar({
            pba_lock_owner_name: "Maria",
            pba_lock_owner_user_id: 4,
        });
        expect(avatar.initial).toBe("M");
        expect(avatar.url).toBe("/web/image/res.users/4/avatar_128");
        expect(avatar.color).toMatch(/^hsl\(/);
    });
});
