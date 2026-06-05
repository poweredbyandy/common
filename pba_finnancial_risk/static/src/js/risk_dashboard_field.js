/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class RiskDashboardField extends Component {
    static props = {
        ...standardFieldProps,
    };

    static template = "pba_finnancial_risk.RiskDashboardField";

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({
            editingField: null,
            value: "",
            saving: false,
        });
    }

    get data() {
        return this.props.record.data[this.props.name] || {};
    }

    get canEdit() {
        return Boolean(this.data.can_edit);
    }

    _formatMoney(value) {
        const amount = Number(value || 0).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
        const symbol = this.data.currency_symbol || "";
        const position = this.data.currency_position || "after";
        return position === "before" ? `${symbol}${amount}` : `${amount} ${symbol}`.trim();
    }

    _canOpenDetail(item) {
        return Boolean(item.risk_field) && Number(item.current || 0) !== 0;
    }

    async _openRiskDetail(item) {
        if (!this._canOpenDetail(item)) {
            return;
        }
        const action = await this.orm.call(
            "res.partner",
            "action_open_risk_detail",
            [[this.props.record.resId], item.risk_field]
        );
        if (action) {
            this.actionService.doAction(action);
        }
    }

    _beginEdit(item) {
        if (!this.canEdit || !item.limit_field || !item.included) {
            return;
        }
        this.state.editingField = item.limit_field;
        this.state.value = String(item.limit || 0);
    }

    _isEditing(item) {
        return this.state.editingField === item.limit_field;
    }

    async _toggleInclude(item, ev) {
        const checked = ev.target.checked;
        if (!this.canEdit || !item.include_field) {
            return;
        }
        const payload = {
            [item.include_field]: checked,
        };
        if (checked && item.include_field === "risk_sale_order_include") {
            payload[item.limit_field] = Number(this.data.credit_limit || 0);
        }
        await this.props.record.update(payload);
    }

    _onInput(ev) {
        this.state.value = ev.target.value;
    }

    async _commitEdit(item) {
        if (!this.canEdit || !item.limit_field || this.state.saving) {
            return;
        }
        const sanitized = (this.state.value || "0").replace(",", ".");
        const parsed = Number.parseFloat(sanitized);
        let value = Number.isFinite(parsed) ? parsed : 0;
        if (item.limit_field === "risk_sale_order_limit" && this.data.credit_limit) {
            value = Math.min(value, Number(this.data.credit_limit));
        }
        this.state.saving = true;
        await this.props.record.update({
            [item.limit_field]: value,
        });
        this.state.saving = false;
        this.state.editingField = null;
    }

    _cancelEdit() {
        this.state.editingField = null;
        this.state.value = "";
    }

    async _onKeydown(item, ev) {
        if (ev.key === "Enter") {
            await this._commitEdit(item);
        } else if (ev.key === "Escape") {
            this._cancelEdit();
        }
    }
}

export const riskDashboardField = {
    component: RiskDashboardField,
    supportedTypes: ["json"],
};

registry.category("fields").add("risk_dashboard", riskDashboardField);
