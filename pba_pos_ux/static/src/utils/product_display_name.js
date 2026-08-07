/** @odoo-module **/

export function getProductDefaultCode(product) {
    if (!product) {
        return "";
    }
    const candidates = [
        product.default_code,
        product.raw?.default_code,
        product.product_tmpl_id?.default_code,
        product.product_tmpl_id?.raw?.default_code,
    ];
    for (const candidate of candidates) {
        if (candidate === undefined || candidate === null || candidate === false) {
            continue;
        }
        const code = candidate.toString().trim();
        if (code) {
            return code;
        }
    }
    return "";
}

export function stripProductDefaultCodePrefix(name = "", product = null) {
    const value = (name || "").toString().trim();
    if (!value) {
        return "";
    }
    const code = getProductDefaultCode(product);
    if (code) {
        const prefix = `[${code}]`;
        if (value === prefix) {
            return product?.name || "";
        }
        if (value.startsWith(`${prefix} `)) {
            return value.slice(prefix.length + 1).trim();
        }
    }
    return value.replace(/^\[[^\]]+\]\s*/, "").trim() || value;
}

export function formatProductDisplayName(product, baseName = "") {
    const name = stripProductDefaultCodePrefix(
        baseName || product?.display_name || product?.name || "",
        product
    );
    const code = getProductDefaultCode(product);
    if (!code) {
        return name;
    }
    const prefix = `[${code}]`;
    if (!name) {
        return prefix;
    }
    return `${prefix} ${name}`;
}
