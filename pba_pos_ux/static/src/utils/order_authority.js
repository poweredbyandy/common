/** @odoo-module **/

export const PBA_AUTOSAVE_DEBOUNCE_MS = 800;

export function isLocalPosOrder(order) {
    return Boolean(order && typeof order.id !== "number");
}

export function shouldPersistPosOrderLocally(order) {
    if (!order || order.state === "cancel" || order.finalized) {
        return false;
    }
    return isLocalPosOrder(order);
}

export function filterIndexedDbPosData(data) {
    if (!data) {
        return data;
    }
    const result = { ...data };
    const localOrders = (data["pos.order"] || []).filter(
        (order) => typeof order.id !== "number"
    );
    const localOrderIds = new Set(localOrders.map((order) => order.id));
    result["pos.order"] = localOrders;

    if (result["pos.order.line"]) {
        result["pos.order.line"] = result["pos.order.line"].filter((line) =>
            localOrderIds.has(line.order_id)
        );
    }
    if (result["pos.payment"]) {
        result["pos.payment"] = result["pos.payment"].filter((payment) =>
            localOrderIds.has(payment.pos_order_id)
        );
    }
    if (result["pos.pack.operation.lot"]) {
        const localLineIds = new Set(
            (result["pos.order.line"] || []).map((line) => line.id)
        );
        result["pos.pack.operation.lot"] = result["pos.pack.operation.lot"].filter(
            (lot) => localLineIds.has(lot.pos_order_line_id)
        );
    }
    if (result["product.attribute.custom.value"]) {
        const localLineIds = new Set(
            (result["pos.order.line"] || []).map((line) => line.id)
        );
        result["product.attribute.custom.value"] = result[
            "product.attribute.custom.value"
        ].filter((value) => localLineIds.has(value.pos_order_line_id));
    }
    return result;
}
