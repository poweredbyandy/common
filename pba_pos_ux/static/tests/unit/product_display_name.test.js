import { describe, expect, test } from "@odoo/hoot";
import {
    formatProductDisplayName,
    getProductDefaultCode,
    stripProductDefaultCodePrefix,
} from "@pba_pos_ux/utils/product_display_name";

describe("pba_pos_ux product display name", () => {
    test("reads default_code from product", () => {
        expect(getProductDefaultCode({ default_code: "108710" })).toBe("108710");
    });

    test("formats list/order name as [default_code] Product", () => {
        expect(
            formatProductDisplayName(
                { default_code: "108710", name: "ALICATE DE PRESION" },
                "ALICATE DE PRESION"
            )
        ).toBe("[108710] ALICATE DE PRESION");
    });

    test("strips code prefix for card title", () => {
        expect(
            stripProductDefaultCodePrefix("[108710] ALICATE DE PRESION", {
                default_code: "108710",
            })
        ).toBe("ALICATE DE PRESION");
    });

    test("does not duplicate existing default_code prefix", () => {
        expect(
            formatProductDisplayName({ default_code: "108710" }, "[108710] ALICATE DE PRESION")
        ).toBe("[108710] ALICATE DE PRESION");
    });
});
