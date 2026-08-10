import { Component, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { SubUserPinDialog } from "./sub_user_lock_screen";

export class SubUserSystray extends Component {
    static template = "res_users_user.SubUserSystray";
    static components = { Dropdown, DropdownItem };
    static props = {};

    setup() {
        this.subUser = useState(useService("sub_user").state);
        this.subUserService = useService("sub_user");
        this.dialog = useService("dialog");
        this.lockLabel = _t("Lock sub-user");
    }

    get displayName() {
        return this.subUser.current_sub_user_name || _t("Sub-user");
    }

    get statusLabel() {
        if (this.subUser.locked) {
            return _t("Locked - select a sub-user");
        }
        if (this.subUser.current_sub_user_name) {
            return _t("Active sub-user");
        }
        return _t("No sub-user selected");
    }

    onSelectSubUser(subUserItem) {
        this.dialog.add(SubUserPinDialog, {
            subUser: subUserItem,
            onConfirm: async (pin) => {
                await this.subUserService.login(subUserItem.id, pin);
            },
        });
    }

    async onLock() {
        await this.subUserService.lock();
    }
}

export const subUserSystrayItem = {
    Component: SubUserSystray,
    isDisplayed: (env) => {
        const subUser = env.services.sub_user;
        return Boolean(subUser?.enabled);
    },
};

registry.category("systray").add("res_users_user.systray", subUserSystrayItem, {
    sequence: 2,
});
