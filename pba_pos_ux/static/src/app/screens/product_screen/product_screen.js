/** @odoo-module **/

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { formatProductDisplayName } from "@pba_pos_ux/utils/product_display_name";
import { patch } from "@web/core/utils/patch";
import { unaccent } from "@web/core/utils/strings";

function normalizeSearchWord(searchWord) {
    return unaccent(String(searchWord || ""), false);
}

function getSearchParts(searchWord) {
    const normalized = normalizeSearchWord(searchWord);
    if (!normalized.includes("*")) {
        return normalized ? [normalized] : [];
    }
    return normalized
        .split("*")
        .map((part) => part.trim())
        .filter(Boolean);
}

function productMatchesSearch(searchString, searchWord) {
    const haystack = unaccent(searchString || "", false);
    const parts = getSearchParts(searchWord);
    if (!parts.length) {
        return true;
    }
    return parts.every((part) => haystack.includes(part));
}

function matchIndex(searchString, searchWord) {
    const haystack = unaccent(searchString || "", false);
    const parts = getSearchParts(searchWord);
    if (!parts.length) {
        return 0;
    }
    return Math.min(...parts.map((part) => haystack.indexOf(part)).filter((idx) => idx >= 0));
}

function buildOrDomain(fields, term) {
    if (!fields.length) {
        return [];
    }
    const leaves = fields.map((field) => [field, "ilike", term]);
    return [...Array(Math.max(fields.length - 1, 0)).fill("|"), ...leaves];
}

patch(ProductScreen.prototype, {
    getProductName(product) {
        return formatProductDisplayName(product, super.getProductName(product));
    },

    getProductDbSearchFields() {
        return ["name", "default_code", "barcode"];
    },

    getProductDbSearchDomain(term) {
        const fields = this.getProductDbSearchFields();
        const parts = getSearchParts(term);
        if (!parts.length) {
            return buildOrDomain(fields, term);
        }
        if (parts.length === 1) {
            return buildOrDomain(fields, parts[0]);
        }
        const domain = [];
        for (let i = 0; i < parts.length - 1; i++) {
            domain.push("&");
        }
        for (const part of parts) {
            domain.push(...buildOrDomain(fields, part));
        }
        return domain;
    },

    getProductsBySearchWord(searchWord) {
        const products = this.pos.selectedCategory?.id
            ? this.getProductsByCategory(this.pos.selectedCategory)
            : this.products;
        const filteredProducts = products.filter((product) =>
            productMatchesSearch(product.searchString || "", searchWord)
        );
        return filteredProducts.sort((a, b) => {
            const nameA = unaccent(a.searchString || "", false);
            const nameB = unaccent(b.searchString || "", false);
            return (
                matchIndex(a.searchString || "", searchWord) -
                    matchIndex(b.searchString || "", searchWord) ||
                nameA.localeCompare(nameB)
            );
        });
    },

    loadProductFromDBDomain(searchProductWord) {
        return [
            ...this.getProductDbSearchDomain(searchProductWord),
            ["available_in_pos", "=", true],
            ["sale_ok", "=", true],
        ];
    },
});
