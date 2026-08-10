/** @odoo-module **/

import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { patch } from "@web/core/utils/patch";
import { unaccent } from "@web/core/utils/strings";

function normalizeSearchWord(searchWord) {
    return unaccent(String(searchWord || ""), false).toLowerCase();
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

function buildOrDomain(fields, term) {
    if (!fields.length) {
        return [];
    }
    const leaves = fields.map((field) => [field, "ilike", term]);
    return [...Array(Math.max(fields.length - 1, 0)).fill("|"), ...leaves];
}

patch(PartnerList, {
    props: {
        ...PartnerList.props,
        forceCustomer: { type: Boolean, optional: true },
    },
});

patch(PartnerList.prototype, {
    clickPartner(partner) {
        if (this.props.forceCustomer && !partner) {
            return;
        }
        return super.clickPartner(...arguments);
    },

    getPartnerDbSearchFields() {
        return [
            "name",
            "parent_name",
            ...this.getPhoneSearchTerms(),
            "email",
            "barcode",
            "street",
            "zip",
            "city",
            "state_id",
            "country_id",
            "vat",
        ];
    },

    getPartnerDbSearchDomain(term) {
        const fields = this.getPartnerDbSearchFields();
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

    getPartners() {
        const searchWord = normalizeSearchWord((this.state.query || "").trim());
        const partners = this.pos.models["res.partner"].getAll();
        if (!searchWord) {
            return partners
                .slice(0, 1000)
                .toSorted((a, b) =>
                    this.props.partner?.id === a.id
                        ? -1
                        : this.props.partner?.id === b.id
                          ? 1
                          : (a.name || "").localeCompare(b.name || "")
                );
        }

        const exactMatches = partners.filter((partner) => partner.exactMatch(searchWord));
        if (exactMatches.length > 0) {
            return exactMatches;
        }

        const parts = getSearchParts(searchWord);
        const numberString = searchWord.replace(/[+\s()-]/g, "");
        const isSearchWordNumber = /^[0-9]+$/.test(numberString);
        const matchParts = isSearchWordNumber ? [numberString] : parts;

        return partners
            .filter((partner) => {
                const haystack = normalizeSearchWord(partner.searchString || "");
                return matchParts.every((part) => haystack.includes(part));
            })
            .slice(0, 200);
    },

    async getNewPartners() {
        if (!this.state.query) {
            return super.getNewPartners(...arguments);
        }
        const result = await this.pos.data.searchRead(
            "res.partner",
            this.getPartnerDbSearchDomain(this.state.query),
            [],
            {
                limit: 30,
                offset: this.state.currentOffset,
            }
        );
        return result;
    },
});
