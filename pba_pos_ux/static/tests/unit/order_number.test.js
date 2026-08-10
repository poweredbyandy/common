import { describe, expect, test } from "@odoo/hoot";
import { getValidPosTrackingNumber } from "@pba_pos_ux/utils/order_number";

describe("pba_pos_ux order number", () => {
    test("keeps a valid tracking number", () => {
        expect(
            getValidPosTrackingNumber({
                trackingNumber: "204",
                sequenceNumber: 4,
                sessionId: 12,
            })
        ).toBe("204");
    });

    test("rebuilds a NaN tracking number from the sequence", () => {
        expect(
            getValidPosTrackingNumber({
                trackingNumber: "NaN",
                sequenceNumber: 4,
                sessionId: 12,
            })
        ).toBe("204");
    });

    test("recovers a missing sequence from the POS reference", () => {
        expect(
            getValidPosTrackingNumber({
                trackingNumber: "NaN",
                sequenceNumber: undefined,
                sessionId: 12,
                posReference: "00012-001-0004",
            })
        ).toBe("204");
    });

    test("does not display NaN when the order cannot be recovered", () => {
        expect(
            getValidPosTrackingNumber({
                trackingNumber: "NaN",
                sequenceNumber: undefined,
                sessionId: undefined,
            })
        ).toBe("");
    });
});
