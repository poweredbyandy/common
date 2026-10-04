import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { formatCurrency } from "@web/core/currency";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class CashBoxOpenDialog extends Component {
    static template = "account_cash_box.CashBoxOpenDialog";
    static components = { Dialog };
    static props = {
        box: Object,
        close: Function,
        onDone: { type: Function, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            counted: this.props.box.accounting_balance,
            notes: "",
            busy: false,
        });
    }

    formatAmount(amount) {
        return formatCurrency(amount, this.props.box.currency_id);
    }

    get difference() {
        return this.state.counted - this.props.box.accounting_balance;
    }

    async confirm() {
        if (this.state.busy) {
            return;
        }
        this.state.busy = true;
        try {
            await this.orm.call("account.cash.box", "action_open_session", [
                [this.props.box.id],
                this.state.counted,
                this.state.notes || false,
            ]);
            this.notification.add(_t("Cash box opened"), { type: "success" });
            this.props.onDone?.();
            this.props.close();
        } catch (error) {
            this.state.busy = false;
            throw error;
        }
    }
}

export class CashBoxMoveDialog extends Component {
    static template = "account_cash_box.CashBoxMoveDialog";
    static components = { Dialog };
    static props = {
        box: Object,
        moveType: String,
        reasons: { type: Array, optional: true },
        close: Function,
        onDone: { type: Function, optional: true },
    };
    static defaultProps = {
        reasons: [],
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        const reasons = this.filteredReasons;
        this.state = useState({
            amount: 0,
            reasonId: reasons[0]?.id || false,
            notes: "",
            busy: false,
        });
    }

    get title() {
        return this.props.moveType === "in" ? _t("Cash In") : _t("Cash Out");
    }

    formatAmount(amount) {
        return formatCurrency(amount, this.props.box.currency_id);
    }

    get filteredReasons() {
        return (this.props.reasons || []).filter(
            (reason) => reason.move_type === this.props.moveType
        );
    }

    async confirm() {
        if (this.state.busy) {
            return;
        }
        if (!this.state.reasonId) {
            this.notification.add(_t("Select a reason"), { type: "danger" });
            return;
        }
        if (!(this.state.amount > 0)) {
            this.notification.add(_t("Enter an amount greater than zero"), {
                type: "danger",
            });
            return;
        }
        this.state.busy = true;
        try {
            await this.orm.call("account.cash.session", "action_register_move", [
                [this.props.box.session_id],
                this.props.moveType,
                this.state.amount,
                this.state.reasonId,
                false,
                this.state.notes || false,
            ]);
            this.notification.add(
                this.props.moveType === "in" ? _t("Cash in registered") : _t("Cash out registered"),
                { type: "success" }
            );
            this.props.onDone?.();
            this.props.close();
        } catch (error) {
            this.state.busy = false;
            throw error;
        }
    }
}

export class CashBoxCloseDialog extends Component {
    static template = "account_cash_box.CashBoxCloseDialog";
    static components = { Dialog };
    static props = {
        box: Object,
        close: Function,
        onDone: { type: Function, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            counted: this.props.box.accounting_balance,
            notes: "",
            busy: false,
        });
    }

    formatAmount(amount) {
        return formatCurrency(amount, this.props.box.currency_id);
    }

    get difference() {
        return this.state.counted - this.props.box.accounting_balance;
    }

    async confirm() {
        if (this.state.busy) {
            return;
        }
        this.state.busy = true;
        try {
            await this.orm.call("account.cash.session", "action_close", [
                [this.props.box.session_id],
                this.state.counted,
                this.state.notes || false,
            ]);
            this.notification.add(_t("Cash box closed"), { type: "success" });
            this.props.onDone?.();
            this.props.close();
        } catch (error) {
            this.state.busy = false;
            throw error;
        }
    }
}

export class CashBoxStatusDialog extends Component {
    static template = "account_cash_box.CashBoxStatusDialog";
    static components = { Dialog };
    static props = {
        status: Object,
        close: Function,
        onOpenSession: { type: Function, optional: true },
        onOpenJournal: { type: Function, optional: true },
    };

    formatAmount(amount) {
        return formatCurrency(amount || 0, this.props.status.currency_id);
    }
}
