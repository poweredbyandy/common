/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { localization } from "@web/core/l10n/localization";
import { formatDate, deserializeDate } from "@web/core/l10n/dates";
import { formatMonetary } from "@web/views/fields/formatters";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component } from "@odoo/owl";

class ExcessRefundPopOver extends Component {
    static props = { "*": { optional: true } };
    static template = "account_payment_excess_refund.ExcessRefundPopOver";
}

export class ExcessRefundField extends Component {
    static props = { ...standardFieldProps };
    static template = "account_payment_excess_refund.ExcessRefundField";

    setup() {
        const position = localization.direction === "rtl" ? "bottom" : "left";
        this.popover = usePopover(ExcessRefundPopOver, { position });
        this.orm = useService("orm");
        this.action = useService("action");
    }

    getInfo() {
        const info = this.props.record.data[this.props.name] || {
            content: [],
            outstanding: false,
            title: "",
            move_id: this.props.record.resId,
        };
        for (const [key, value] of Object.entries(info.content || {})) {
            value.index = key;
            value.amount_formatted = formatMonetary(value.amount, {
                currencyId: value.currency_id,
            });
            if (value.date) {
                value.formattedDate = formatDate(deserializeDate(value.date));
            }
        }
        return {
            lines: info.content || [],
            outstanding: info.outstanding,
            title: info.title,
            moveId: info.move_id,
        };
    }

    onInfoClick(ev, line) {
        this.popover.open(ev.currentTarget, {
            title: _t("Excess Refund Info"),
            ...line,
            _onCancelPayment: this.cancelPayment.bind(this),
            _onOpenPayment: this.openPayment.bind(this),
            _onOpenMove: this.openMove.bind(this),
        });
    }

    async returnExcess(moveId, lineId) {
        const action = await this.orm.call(
            this.props.record.resModel,
            "js_action_return_excess_line",
            [moveId, lineId],
            {}
        );
        if (action) {
            await this.action.doAction(action, {
                onClose: async () => {
                    await this.props.record.model.root.load();
                },
            });
        } else {
            await this.props.record.model.root.load();
        }
    }

    async cancelPayment(paymentId) {
        this.popover.close();
        await this.orm.call(
            this.props.record.resModel,
            "js_action_cancel_excess_refund_payment",
            [this.props.record.resId, paymentId],
            {}
        );
        await this.props.record.model.root.load();
    }

    async openPayment(paymentId) {
        this.popover.close();
        const action = await this.orm.call(
            this.props.record.resModel,
            "js_action_open_excess_refund_payment",
            [this.props.record.resId, paymentId],
            {}
        );
        this.action.doAction(action);
    }

    async openMove(moveId) {
        this.popover.close();
        const action = await this.orm.call(
            this.props.record.resModel,
            "action_open_business_doc",
            [moveId],
            {}
        );
        this.action.doAction(action);
    }
}

export const excessRefundField = {
    component: ExcessRefundField,
    supportedTypes: ["char"],
};

registry.category("fields").add("excess_refund", excessRefundField);
