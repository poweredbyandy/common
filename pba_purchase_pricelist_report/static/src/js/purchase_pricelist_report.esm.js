/** @odoo-module **/

import {ProductPricelistReport} from "@product/js/pricelist_report/product_pricelist_report";
import {patch} from "@web/core/utils/patch";

patch(ProductPricelistReport.prototype, {
    get reportParams() {
        const params = super.reportParams;
        const excelTitle = this.props.action.context.pricelist_excel_title;
        if (excelTitle) {
            params.pricelist_excel_title = excelTitle;
        }
        return params;
    },
});
