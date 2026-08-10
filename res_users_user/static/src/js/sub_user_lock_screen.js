import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

const PAD_KEYS = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "C", "0", "BS"];

export class SubUserPinDialog extends Component {
    static template = "res_users_user.SubUserPinDialog";
    static components = { Dialog };
    static props = {
        close: Function,
        subUser: Object,
        onConfirm: Function,
    };

    setup() {
        this.state = useState({ pin: "", error: "" });
        this.padKeys = PAD_KEYS;
        this.title = _t("Enter PIN - %(name)s", { name: this.props.subUser.name });
        this.confirmLabel = _t("Confirm");
        this.cancelLabel = _t("Cancel");
        this.clearLabel = _t("C");
    }

    onPinInput(ev) {
        this.state.pin = (ev.target.value || "").replace(/\D/g, "");
        this.state.error = "";
    }

    onPadKey(key) {
        if (key === "C") {
            this.state.pin = "";
        } else if (key === "BS") {
            this.state.pin = this.state.pin.slice(0, -1);
        } else {
            this.state.pin += key;
        }
        this.state.error = "";
    }

    async onPinKeydown(ev) {
        if (ev.key === "Enter") {
            await this.onConfirm();
        }
    }

    async onConfirm() {
        if (!this.state.pin) {
            return;
        }
        try {
            await this.props.onConfirm(this.state.pin);
            this.props.close();
        } catch (error) {
            this.state.error = error.data?.message || error.message || _t("Incorrect PIN.");
            this.state.pin = "";
        }
    }
}

export class SubUserLockScreen extends Component {
    static template = "res_users_user.SubUserLockScreen";
    static props = {};

    setup() {
        this.subUserService = useService("sub_user");
        this.subUser = useState(this.subUserService.state);
        this.state = useState({
            selectedId: false,
            pin: "",
            error: "",
        });
        this.padKeys = PAD_KEYS;
        this.title = _t("Select sub-user");
        this.subtitle = _t("Choose a seller and enter the PIN to continue.");
        this.pinLabel = _t("PIN");
        this.confirmLabel = _t("Unlock");
        this.clearLabel = _t("C");
    }

    selectSubUser(item) {
        this.state.selectedId = item.id;
        this.state.pin = "";
        this.state.error = "";
    }

    onPinInput(ev) {
        this.state.pin = (ev.target.value || "").replace(/\D/g, "");
        this.state.error = "";
    }

    onPadKey(key) {
        if (key === "C") {
            this.state.pin = "";
        } else if (key === "BS") {
            this.state.pin = this.state.pin.slice(0, -1);
        } else {
            this.state.pin += key;
        }
        this.state.error = "";
    }

    async onPinKeydown(ev) {
        if (ev.key === "Enter") {
            await this.onConfirm();
        }
    }

    async onConfirm() {
        if (!this.state.selectedId || !this.state.pin) {
            return;
        }
        try {
            await this.subUserService.login(this.state.selectedId, this.state.pin);
            this.state.pin = "";
            this.state.error = "";
        } catch (error) {
            this.state.error = error.data?.message || error.message || _t("Incorrect PIN.");
            this.state.pin = "";
        }
    }
}

registry.category("main_components").add("res_users_user.LockScreen", {
    Component: SubUserLockScreen,
});
