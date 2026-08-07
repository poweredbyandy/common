/** @odoo-module **/

/**
 * Pure helpers for POS free qty display/sync (unit-testable).
 */

export function getProductFreeQty(product, productFreeQty = {}) {
    if (!product) {
        return 0;
    }
    if (productFreeQty[product.id] !== undefined) {
        return productFreeQty[product.id];
    }
    return product.free_qty ?? 0;
}

export function applyFreeQtyMap(productFreeQty, qtyByProduct, productsById = {}) {
    const next = { ...productFreeQty };
    for (const [productId, freeQty] of Object.entries(qtyByProduct || {})) {
        const id = parseInt(productId, 10);
        if (Number.isNaN(id)) {
            continue;
        }
        next[id] = freeQty;
        const product = productsById[id];
        if (product) {
            product.free_qty = freeQty;
        }
    }
    return next;
}

export function applyOrderFreeQtyDecrement({
    productFreeQty,
    appliedOrders,
    order,
    revert = false,
    enabled = true,
}) {
    const nextQty = { ...productFreeQty };
    const nextApplied = new Set(appliedOrders);
    if (!enabled || !order?.uuid) {
        return { productFreeQty: nextQty, appliedOrders: nextApplied };
    }
    const orderKey = order.uuid;
    if (!revert && nextApplied.has(orderKey)) {
        return { productFreeQty: nextQty, appliedOrders: nextApplied };
    }
    if (revert && !nextApplied.has(orderKey)) {
        return { productFreeQty: nextQty, appliedOrders: nextApplied };
    }
    const factor = revert ? 1 : -1;
    const soldByProduct = {};
    for (const line of order.lines || []) {
        const product = line.product;
        if (!product?.is_storable) {
            continue;
        }
        soldByProduct[product.id] = (soldByProduct[product.id] || 0) + (line.qty || 0);
    }
    for (const [productId, qty] of Object.entries(soldByProduct)) {
        const id = parseInt(productId, 10);
        const current = nextQty[id] !== undefined ? nextQty[id] : productFreeQty[id] ?? 0;
        nextQty[id] = current + factor * qty;
    }
    if (revert) {
        nextApplied.delete(orderKey);
    } else {
        nextApplied.add(orderKey);
    }
    return { productFreeQty: nextQty, appliedOrders: nextApplied };
}

export function shouldAcceptFreeQtyNotify(payload, configWarehouseId) {
    const warehouseId = payload?.warehouse_id;
    if (warehouseId && configWarehouseId && warehouseId !== configWarehouseId) {
        return false;
    }
    return true;
}

export function getDisplayAvailableQty(baseQty, orderedQty = 0) {
    return (baseQty || 0) - (orderedQty || 0);
}

export function getQtyAvailableLevel(qty) {
    if (qty <= 0) {
        return "out";
    }
    if (qty < 5) {
        return "low";
    }
    return "ok";
}
