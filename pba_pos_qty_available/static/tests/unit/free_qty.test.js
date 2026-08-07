import { describe, expect, test } from "@odoo/hoot";
import {
    applyFreeQtyMap,
    applyOrderFreeQtyDecrement,
    getDisplayAvailableQty,
    getProductFreeQty,
    getQtyAvailableLevel,
    shouldAcceptFreeQtyNotify,
} from "@pba_pos_qty_available/app/utils/free_qty";

describe("pba_pos_qty_available free_qty utils", () => {
    test("getProductFreeQty prefers reactive map over product field", () => {
        const product = { id: 7, free_qty: 10 };
        expect(getProductFreeQty(product, {})).toBe(10);
        expect(getProductFreeQty(product, { 7: 3 })).toBe(3);
        expect(getProductFreeQty(null, {})).toBe(0);
    });

    test("applyFreeQtyMap updates map and product records", () => {
        const product = { id: 5, free_qty: 0 };
        const next = applyFreeQtyMap({}, { 5: 42, "x": 1 }, { 5: product });
        expect(next[5]).toBe(42);
        expect(product.free_qty).toBe(42);
        expect(next.x).toBe(undefined);
    });

    test("applyOrderFreeQtyDecrement reduces qty once per order uuid", () => {
        const product = { id: 11, is_storable: true, free_qty: 100 };
        const order = {
            uuid: "order-a",
            lines: [{ product, qty: 4 }],
        };
        const first = applyOrderFreeQtyDecrement({
            productFreeQty: { 11: 100 },
            appliedOrders: new Set(),
            order,
        });
        expect(first.productFreeQty[11]).toBe(96);
        expect(first.appliedOrders.has("order-a")).toBe(true);

        const second = applyOrderFreeQtyDecrement({
            productFreeQty: first.productFreeQty,
            appliedOrders: first.appliedOrders,
            order,
        });
        expect(second.productFreeQty[11]).toBe(96);

        const reverted = applyOrderFreeQtyDecrement({
            productFreeQty: second.productFreeQty,
            appliedOrders: second.appliedOrders,
            order,
            revert: true,
        });
        expect(reverted.productFreeQty[11]).toBe(100);
        expect(reverted.appliedOrders.has("order-a")).toBe(false);
    });

    test("applyOrderFreeQtyDecrement ignores non-storable products", () => {
        const service = { id: 2, is_storable: false };
        const result = applyOrderFreeQtyDecrement({
            productFreeQty: {},
            appliedOrders: new Set(),
            order: {
                uuid: "svc",
                lines: [{ product: service, qty: 3 }],
            },
        });
        expect(result.productFreeQty[2]).toBe(undefined);
    });

    test("shouldAcceptFreeQtyNotify filters by warehouse", () => {
        expect(shouldAcceptFreeQtyNotify({ warehouse_id: 1 }, 1)).toBe(true);
        expect(shouldAcceptFreeQtyNotify({ warehouse_id: 2 }, 1)).toBe(false);
        expect(shouldAcceptFreeQtyNotify({}, 1)).toBe(true);
    });

    test("display qty and level helpers", () => {
        expect(getDisplayAvailableQty(10, 3)).toBe(7);
        expect(getQtyAvailableLevel(0)).toBe("out");
        expect(getQtyAvailableLevel(3)).toBe("low");
        expect(getQtyAvailableLevel(20)).toBe("ok");
    });
});
