import { Component, onWillStart, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { formatCurrency } from "@web/core/currency";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import {
    CashBoxCloseDialog,
    CashBoxMoveDialog,
    CashBoxOpenDialog,
    CashBoxStatusDialog,
} from "./cash_box_dialogs";

export class CashBoxSystray extends Component {
    static template = "account_cash_box.CashBoxSystray";
    static components = { Dropdown };
    static props = [];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.dialog = useService("dialog");
        this.dropdown = useDropdownState();
        this.state = useState({
            boxes: [],
            reasons: [],
            isManager: false,
            loaded: false,
        });
        onWillStart(async () => {
            const hasGroup = await user.hasGroup("account_cash_box.group_cash_box_user");
            if (hasGroup) {
                await this.refresh();
            }
            this.state.loaded = true;
        });
    }

    get openCount() {
        return this.state.boxes.filter((box) => box.state === "open").length;
    }

    get visible() {
        return this.state.loaded && this.state.boxes.length;
    }

    formatAmount(box, amount) {
        return formatCurrency(amount || 0, box.currency_id);
    }

    async refresh() {
        const [data, reasons] = await Promise.all([
            this.orm.call("account.cash.box", "get_systray_data", []),
            this.orm.call("account.cash.reason", "get_systray_reasons", []),
        ]);
        this.state.boxes = data.boxes || [];
        this.state.isManager = Boolean(data.is_manager);
        this.state.reasons = reasons || [];
    }

    async onBeforeOpen() {
        await this.refresh();
    }

    openOpenDialog(box) {
        this.dropdown.close();
        this.dialog.add(CashBoxOpenDialog, {
            box,
            onDone: () => this.refresh(),
        });
    }

    openMoveDialog(box, moveType) {
        this.dropdown.close();
        this.dialog.add(CashBoxMoveDialog, {
            box,
            moveType,
            reasons: this.state.reasons,
            onDone: () => this.refresh(),
        });
    }

    openCloseDialog(box) {
        this.dropdown.close();
        this.dialog.add(CashBoxCloseDialog, {
            box,
            onDone: () => this.refresh(),
        });
    }

    async openStatusDialog(box) {
        this.dropdown.close();
        const status = await this.orm.call("account.cash.box", "get_status_data", [
            [box.id],
        ]);
        this.dialog.add(CashBoxStatusDialog, {
            status,
            onOpenSession: () => {
                if (status.session_id) {
                    this.action.doAction({
                        type: "ir.actions.act_window",
                        name: status.session_name || _t("Session"),
                        res_model: "account.cash.session",
                        res_id: status.session_id,
                        views: [[false, "form"]],
                        target: "current",
                    });
                }
            },
            onOpenJournal: () => {
                this.action.doAction({
                    type: "ir.actions.act_window",
                    name: _t("Journal Items"),
                    res_model: "account.move.line",
                    views: [
                        [false, "list"],
                        [false, "form"],
                    ],
                    domain: [
                        ["account_id", "=", status.cash_account_id],
                        ["display_type", "not in", ["line_section", "line_note"]],
                    ],
                    context: { search_default_posted: 1 },
                    target: "current",
                });
            },
        });
    }
}

registry.category("systray").add(
    "account_cash_box.CashBoxSystray",
    { Component: CashBoxSystray },
    { sequence: 25 }
);
