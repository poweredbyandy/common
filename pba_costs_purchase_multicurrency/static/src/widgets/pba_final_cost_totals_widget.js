/** @odoo-module **/

import {Component, onWillRender} from "@odoo/owl";
import {formatMonetary} from "@web/views/fields/formatters";
import {registry} from "@web/core/registry";
import {standardFieldProps} from "@web/views/fields/standard_field_props";

export class PbaFinalCostTotalsWidget extends Component {
    static props = {...standardFieldProps};
    static template = "pba_costs_purchase_multicurrency.PbaFinalCostTotalsWidget";

    setup() {
        super.setup();
        this.totals = [];
        this.hasResidual = false;
        this.formatData(this.props);
        onWillRender(() => this.formatData(this.props));
    }

    formatData(props) {
        const raw = props.record.data[this.props.name];
        if (!raw) {
            this.totals = [];
            this.hasResidual = false;
            return;
        }
        const totals = typeof raw === "string" ? JSON.parse(raw) : raw;
        if (!totals) {
            this.totals = [];
            this.hasResidual = false;
            return;
        }
        this.totals = Object.values(totals);
        this.hasResidual = this.totals.length > 0 && "residual" in this.totals[0];
    }

    formatAmount(total, key) {
        return formatMonetary(total[key], {currencyId: total.currency_id});
    }
}

registry
    .category("fields")
    .add("pba_final_cost_totals_widget", {component: PbaFinalCostTotalsWidget});
