/** @odoo-module */

import {patch} from "@web/core/utils/patch";
import {formatMonetary} from "@web/views/fields/formatters";
import {ProductCatalogOrderLine} from "@product/product_catalog/order_line/order_line";

patch(ProductCatalogOrderLine.prototype, {
    get pricelists() {
        return this.props.pricelists || [];
    },

    formatPrice(price, currencyId, digits) {
        const {currencyId: envCurrencyId, digits: envDigits} = this.env;
        return formatMonetary(price, {
            currencyId: currencyId || envCurrencyId,
            digits: digits || envDigits || [false, 2],
        });
    },

    get showPricelists() {
        const pricelists = this.pricelists;
        return pricelists && pricelists.length > 0;
    },

    get showForeignPriceColumn() {
        return this.pricelists.some(
            (pricelist) => pricelist.currency_id !== pricelist.company_currency_id
        );
    },
});
