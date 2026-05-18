/** @odoo-module **/

import {ProductPricelistReport} from "@product/js/pricelist_report/product_pricelist_report";
import {patch} from "@web/core/utils/patch";

patch(ProductPricelistReport.prototype, {
    get reportParams() {
        const params = super.reportParams;
        const reportSource = this.props.action.context.pricelist_report_source;
        if (reportSource) {
            params.pricelist_report_source = reportSource;
        }
        return params;
    },
});
