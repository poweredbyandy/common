/** @odoo-module **/

export const PBA_DEVICE_TOKEN_KEY = "pba_pos_ux_device_token";
export const PBA_LOCK_HEARTBEAT_MS = 10000;

export function createDeviceToken() {
    if (typeof crypto !== "undefined" && crypto.randomUUID) {
        return crypto.randomUUID();
    }
    return `pba-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function getOrCreateDeviceToken(storage = window.sessionStorage) {
    let token = null;
    try {
        token = storage?.getItem?.(PBA_DEVICE_TOKEN_KEY) || null;
    } catch (_error) {
        token = null;
    }
    if (!token) {
        token = createDeviceToken();
        try {
            storage?.setItem?.(PBA_DEVICE_TOKEN_KEY, token);
        } catch (_error) {
            // Keep in-memory token if storage is unavailable.
        }
    }
    return token;
}

export function isSharedPosOrder(order) {
    return Boolean(order && typeof order.id === "number");
}

export function parsePosLockExpireMs(expire) {
    if (expire == null || expire === false || expire === "") {
        return NaN;
    }
    if (typeof expire === "number") {
        return expire;
    }
    const value = String(expire).trim();
    if (!value) {
        return NaN;
    }
    const normalized = value.includes("T") ? value : value.replace(" ", "T");
    const withZone = /(?:[zZ]|[+-]\d{2}:?\d{2})$/.test(normalized)
        ? normalized
        : `${normalized}Z`;
    return Date.parse(withZone);
}

export function isPosOrderLockActive(order, now = Date.now()) {
    if (!order || !order.pba_lock_device_token || !order.pba_lock_expire) {
        return false;
    }
    const expireMs = parsePosLockExpireMs(order.pba_lock_expire);
    return Number.isFinite(expireMs) && expireMs > now;
}

export function isPosOrderLockedByOther(order, deviceToken, now = Date.now()) {
    if (!isPosOrderLockActive(order, now)) {
        return false;
    }
    return order.pba_lock_device_token !== deviceToken;
}

export function isPosOrderOccupied(order, now = Date.now()) {
    return isPosOrderLockActive(order, now);
}

export function getPosOrderLockOwnerName(order) {
    return order?.pba_lock_owner_name || "";
}

export function getPosOrderLockOwnerAvatarUrl(order) {
    if (order?.pba_lock_owner_employee_id) {
        return `/web/image/hr.employee.public/${order.pba_lock_owner_employee_id}/avatar_128`;
    }
    if (order?.pba_lock_owner_user_id) {
        return `/web/image/res.users/${order.pba_lock_owner_user_id}/avatar_128`;
    }
    return "";
}

export function getPosOrderLockOwnerAvatarInitial(name) {
    const trimmed = String(name || "").trim();
    return trimmed ? trimmed[0].toUpperCase() : "?";
}

function hashSeed(seed) {
    let hash = 0;
    const value = String(seed || "");
    for (let i = 0; i < value.length; i++) {
        hash = (hash << 5) - hash + value.charCodeAt(i);
        hash |= 0;
    }
    return Math.abs(hash);
}

export function getPosOrderLockOwnerAvatarColor(name, id = 0) {
    const hash = hashSeed(`${name || ""}${id || ""}`);
    const hue = hash % 360;
    const sat = 40 + (hash % 31);
    return `hsl(${hue}, ${sat}%, 45%)`;
}

export function getPosOrderLockOwnerAvatar(order) {
    const name = getPosOrderLockOwnerName(order);
    const id = order?.pba_lock_owner_employee_id || order?.pba_lock_owner_user_id || 0;
    return {
        name,
        initial: getPosOrderLockOwnerAvatarInitial(name),
        color: getPosOrderLockOwnerAvatarColor(name, id),
        url: getPosOrderLockOwnerAvatarUrl(order),
    };
}

export function countPendingPosOrders({ orderToCreate = [], orderToUpdate = [], unsyncData = [] } = {}) {
    return orderToCreate.length + orderToUpdate.length + unsyncData.length;
}
