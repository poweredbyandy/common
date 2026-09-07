/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { QtyAtDateWidget } from "@sale_stock/widgets/qty_at_date_widget";

const AVAILABILITY_COLOR_CLASS = {
    in_stock: "text-success",
    forecasted: "o_sale_stock_availability_color_forecasted",
    unavailable: "text-danger",
};

patch(QtyAtDateWidget.prototype, {
    get availabilityColorClass() {
        return AVAILABILITY_COLOR_CLASS[this.props.record.data.qty_availability_state] || "";
    },
});
