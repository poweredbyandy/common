/** @odoo-module **/

function parseFiniteInteger(value) {
    const parsed = Number.parseInt(value, 10);
    return Number.isFinite(parsed) ? parsed : false;
}

export function getValidPosTrackingNumber({
    trackingNumber,
    sequenceNumber,
    sessionId,
    posReference,
}) {
    if (parseFiniteInteger(trackingNumber) !== false) {
        return String(trackingNumber);
    }

    let sequence = parseFiniteInteger(sequenceNumber);
    if (sequence === false) {
        const match = String(posReference || "").match(/-(\d+)$/);
        sequence = match ? parseFiniteInteger(match[1]) : false;
    }

    const session = parseFiniteInteger(sessionId);
    if (sequence === false || session === false) {
        return "";
    }
    return String((session % 10) * 100 + (sequence % 100));
}
