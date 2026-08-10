/** @odoo-module **/

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { formatProductDisplayName } from "@pba_pos_ux/utils/product_display_name";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { unaccent } from "@web/core/utils/strings";
import { useEffect, useExternalListener } from "@odoo/owl";

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
    setup() {
        super.setup(...arguments);
        this.state.listKeyboardIndex = -1;
        this.state.searchInputFocused = false;
        useExternalListener(window, "keydown", this._pbaOnListKeyboardNav, {
            capture: true,
        });
        useExternalListener(window, "focusin", this._pbaOnSearchFocusChange, {
            capture: true,
        });
        useExternalListener(window, "focusout", this._pbaOnSearchFocusChange, {
            capture: true,
        });
        useEffect(
            () => {
                this._pbaSyncListKeyboardSelection({ resetToFirst: true });
            },
            () => [this.pos.searchProductWord, this.pos.productListView]
        );
    },

    get currentOrder() {
        return this.pos.get_order() || this.pos.pbaGetNoOrderStub();
    },

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

    async loadProductFromDB() {
        if (!this.pos.searchProductWord) {
            return;
        }
        this.ui.block({ message: _t("Loading products...") });
        try {
            return await super.loadProductFromDB(...arguments);
        } finally {
            this.ui.unblock();
        }
    },

    _pbaIsListView() {
        return (this.pos.productListView || "grid") === "list";
    },

    getProductCardClass(product) {
        const classes = [this.pos.productViewMode || ""];
        if (this.isListKeyboardSelected(product)) {
            classes.push("pba_pos_ux_list_selected");
        }
        return classes.filter(Boolean).join(" ");
    },

    isListKeyboardSelected(product) {
        if (
            !this._pbaIsListView() ||
            !this.state.searchInputFocused ||
            this.state.listKeyboardIndex < 0 ||
            !product
        ) {
            return false;
        }
        const selected = this.productsToDisplay[this.state.listKeyboardIndex];
        return Boolean(selected && selected.id === product.id);
    },

    _pbaOnSearchFocusChange() {
        requestAnimationFrame(() => {
            const focused = this._pbaIsSearchInputFocused();
            if (this.state.searchInputFocused === focused) {
                return;
            }
            this.state.searchInputFocused = focused;
            this._pbaSyncListKeyboardSelection({ resetToFirst: focused });
        });
    },

    _pbaSyncListKeyboardSelection({ resetToFirst = false } = {}) {
        if (!this._pbaIsListView() || !this.state.searchInputFocused) {
            this.state.listKeyboardIndex = -1;
            return;
        }
        const products = this.productsToDisplay;
        if (!products.length || !this.searchWord) {
            this.state.listKeyboardIndex = -1;
            return;
        }
        if (resetToFirst || this.state.listKeyboardIndex < 0) {
            this.state.listKeyboardIndex = 0;
        } else if (this.state.listKeyboardIndex >= products.length) {
            this.state.listKeyboardIndex = products.length - 1;
        }
        this._pbaScrollSelectedIntoView();
    },

    _pbaMoveListSelection(step) {
        if (!this.state.searchInputFocused) {
            return;
        }
        const products = this.productsToDisplay;
        if (!products.length) {
            this.state.listKeyboardIndex = -1;
            return;
        }
        let nextIndex = this.state.listKeyboardIndex;
        if (nextIndex < 0) {
            nextIndex = step > 0 ? 0 : products.length - 1;
        } else {
            nextIndex = Math.min(Math.max(nextIndex + step, 0), products.length - 1);
        }
        this.state.listKeyboardIndex = nextIndex;
        this._pbaScrollSelectedIntoView();
    },

    _pbaScrollSelectedIntoView() {
        const product = this.productsToDisplay[this.state.listKeyboardIndex];
        if (!product) {
            return;
        }
        requestAnimationFrame(() => {
            document
                .querySelector(
                    `.rightpane .product-list [data-product-id="${product.id}"]`
                )
                ?.scrollIntoView({ block: "nearest", behavior: "smooth" });
        });
    },

    _pbaIsSearchInputFocused(el = document.activeElement) {
        if (!el) {
            return false;
        }
        return Boolean(
            el.matches?.(
                ".pba_pos_ux_product_search input, .pos-rightheader .input-container input"
            ) ||
                el.closest?.(
                    ".pba_pos_ux_product_search, .pos-rightheader .input-container"
                )
        );
    },

    _pbaFocusProductSearch() {
        const input = document.querySelector(
            ".pba_pos_ux_product_search input, .pos-rightheader .input-container input"
        );
        if (!input) {
            return;
        }
        input.focus();
        const value = input.value || "";
        input.setSelectionRange(value.length, value.length);
    },

    _pbaFocusOrderSelection() {
        this.state.listKeyboardIndex = -1;
        this.state.searchInputFocused = false;
        const order = this.currentOrder || this.pos.get_order();
        if (!order?.lines?.length) {
            document.activeElement?.blur?.();
            return false;
        }
        let line = order.get_selected_orderline();
        if (!line) {
            line = order.lines.at(-1);
        }
        order.select_orderline(line);
        document.activeElement?.blur?.();
        this.numberBuffer?.reset?.();
        requestAnimationFrame(() => {
            document
                .querySelector(".leftpane .orderline.selected, .leftpane .orderline")
                ?.scrollIntoView?.({ block: "nearest" });
        });
        return true;
    },

    _pbaCanHandleListKeyboard(ev) {
        if (!this._pbaIsListView() || this.pos.scanning) {
            return false;
        }
        if (!this._pbaIsSearchInputFocused(ev.target) && !this.state.searchInputFocused) {
            return false;
        }
        if (document.querySelector(".o_dialog .modal-dialog, .modal.show .modal-dialog")) {
            return false;
        }
        return true;
    },

    _pbaStopKeyboardEvent(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        if (typeof ev.stopImmediatePropagation === "function") {
            ev.stopImmediatePropagation();
        }
    },

    _pbaClearProductSearch() {
        this.pos.searchProductWord = "";
        this.state.listKeyboardIndex = -1;
        const input = document.querySelector(
            ".pba_pos_ux_product_search input, .pos-rightheader .input-container input"
        );
        if (input && input.value) {
            input.value = "";
        }
        this._pbaFocusProductSearch();
    },

    async _pbaOnListKeyboardNav(ev) {
        if (!this._pbaCanHandleListKeyboard(ev)) {
            return;
        }
        if (ev.key === "ArrowDown") {
            this._pbaStopKeyboardEvent(ev);
            this._pbaMoveListSelection(1);
            return;
        }
        if (ev.key === "ArrowUp") {
            this._pbaStopKeyboardEvent(ev);
            this._pbaMoveListSelection(-1);
            return;
        }
        if (ev.key === "Backspace" || ev.key === "Delete") {
            const hasSearch = Boolean(
                this.searchWord || this.pos.searchProductWord?.trim?.()
            );
            const hasListFocus = this.state.listKeyboardIndex >= 0;

            if (hasListFocus && hasSearch) {
                this._pbaStopKeyboardEvent(ev);
                this._pbaClearProductSearch();
                return;
            }

            if (!hasSearch) {
                this._pbaStopKeyboardEvent(ev);
                this._pbaFocusOrderSelection();
            }
            return;
        }
        if (ev.key === "Enter") {
            const product = this.productsToDisplay[this.state.listKeyboardIndex];
            if (!product) {
                return;
            }
            this._pbaStopKeyboardEvent(ev);
            await this.addProductToOrder(product);
        }
    },
});
