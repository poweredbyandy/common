/** @odoo-module **/

import {
    ProductLabelSectionAndNoteField,
    ProductLabelSectionAndNoteFieldAutocomplete,
} from "@account/components/product_label_section_and_note_field/product_label_section_and_note_field";
import {
    SaleOrderLineProductField,
    saleOrderLineProductField,
} from "@sale/js/sale_product_field";
import { registry } from "@web/core/registry";
import { formatFloat } from "@web/views/fields/formatters";

export function qtyBadgeClass(qty) {
    const value = qty || 0;
    if (value <= 0) {
        return "text-bg-danger";
    }
    if (value <= 5) {
        return "text-bg-warning";
    }
    return "text-bg-success";
}

export function formatQtyBadge(qty) {
    return formatFloat(qty || 0, { digits: [16, 2] });
}

export class SaleProductQtyAutocomplete extends ProductLabelSectionAndNoteFieldAutocomplete {
    get showProductQty() {
        return Boolean(this.props.context?.sale_product_search_show_qty);
    }

    get optionsSource() {
        const source = super.optionsSource;
        if (!this.showProductQty) {
            return source;
        }
        return {
            ...source,
            optionTemplate: "sale_product_search_qty.ProductQtyDropdownOption",
        };
    }

    mapRecordToOption(result) {
        const option = super.mapRecordToOption(...arguments);
        if (this.showProductQty) {
            option.classList = `${option.classList || ""} o_sale_product_qty_option`.trim();
        }
        return option;
    }

    async loadOptionsSource(request) {
        const options = await super.loadOptionsSource(...arguments);
        if (!this.showProductQty) {
            return options;
        }
        return this._appendQtyBadges(options);
    }

    async _appendQtyBadges(options) {
        const productOptions = options.filter(
            (option) => Number.isInteger(option.value) && !option.action
        );
        if (!productOptions.length) {
            return options;
        }

        const records = await this.orm.read(
            this.props.resModel,
            productOptions.map((option) => option.value),
            ["qty_available"],
            { context: this.props.context }
        );
        const recordsById = Object.fromEntries(records.map((record) => [record.id, record]));

        return options.map((option) => {
            if (!Number.isInteger(option.value) || option.action) {
                return option;
            }
            const record = recordsById[option.value];
            if (!record) {
                return option;
            }
            const qtyAvailable = record.qty_available || 0;
            return {
                ...option,
                qtyAvailable,
                qtyFormatted: formatQtyBadge(qtyAvailable),
                qtyBadgeClass: qtyBadgeClass(qtyAvailable),
            };
        });
    }
}

export class SaleProductQtyProductField extends SaleOrderLineProductField {
    static components = {
        ...ProductLabelSectionAndNoteField.components,
        Many2XAutocomplete: SaleProductQtyAutocomplete,
    };
}

registry.category("fields").add(
    "sol_product_many2one",
    {
        ...saleOrderLineProductField,
        component: SaleProductQtyProductField,
    },
    { force: true }
);
