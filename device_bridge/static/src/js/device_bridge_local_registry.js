/** @odoo-module **/

const localProxies = new Map();
const localGateways = new Map();

export function setLocalProxy(deviceCode, proxy) {
    if (!deviceCode) {
        return;
    }
    if (proxy) {
        localProxies.set(deviceCode, proxy);
    } else {
        localProxies.delete(deviceCode);
    }
}

export function getLocalProxy(deviceCode) {
    return localProxies.get(deviceCode) || null;
}

export function setLocalGateway(deviceCode, gateway) {
    if (!deviceCode) {
        return;
    }
    if (gateway) {
        localGateways.set(deviceCode, gateway);
    } else {
        localGateways.delete(deviceCode);
    }
}

export function getLocalGateway(deviceCode) {
    return localGateways.get(deviceCode) || null;
}

export function listLocalGateways() {
    return [...localGateways.entries()];
}
