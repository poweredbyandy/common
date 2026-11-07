import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { _t } from "@web/core/l10n/translation";

import { Component, onWillStart, useState } from "@odoo/owl";

export class GmailSystray extends Component {
    static template = "mail_gmail_user.GmailSystray";
    static components = { Dropdown, DropdownItem };
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            visible: false,
            connected: false,
            email: "",
            company_email: "",
            last_error: false,
            account_id: false,
            loading: true,
        });
        onWillStart(async () => {
            await this.refresh();
        });
    }

    async refresh() {
        const info = await this.orm.call("res.users", "mail_gmail_systray_info", []);
        Object.assign(this.state, {
            visible: Boolean(info.visible),
            connected: Boolean(info.connected),
            email: info.email || "",
            company_email: info.company_email || "",
            last_error: info.last_error || false,
            account_id: info.account_id || false,
            loading: false,
        });
    }

    get title() {
        if (this.state.connected) {
            return _t("Gmail connected: %(email)s", { email: this.state.email });
        }
        return _t("Gmail disconnected");
    }

    get iconClass() {
        return this.state.connected
            ? "fa fa-envelope o_mail_gmail_user_icon o_mail_gmail_user_connected"
            : "fa fa-envelope o_mail_gmail_user_icon o_mail_gmail_user_disconnected";
    }

    async onConnect() {
        const action = await this.orm.call("mail.gmail.account", "action_connect_current_user", []);
        await this.action.doAction(action);
    }

    async onDisconnect() {
        if (!this.state.account_id) {
            return;
        }
        await this.orm.call("mail.gmail.account", "action_disconnect", [[this.state.account_id]]);
        this.notification.add(_t("Gmail disconnected"), { type: "warning" });
        await this.refresh();
    }
}

export const gmailSystrayItem = {
    Component: GmailSystray,
    isDisplayed: () => Boolean(user.isInternalUser),
};

registry.category("systray").add("mail_gmail_user.GmailSystray", gmailSystrayItem, {
    sequence: 25,
});
