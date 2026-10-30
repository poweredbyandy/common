/* @odoo-module */

import { ActionPanel } from "@mail/discuss/core/common/action_panel";

import { Component, onMounted, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class WhatsappResponsiblePanel extends Component {
    static components = { ActionPanel };
    static defaultProps = { hasSizeConstraints: false };
    static props = ["hasSizeConstraints?", "thread", "close", "className?"];
    static template = "mail_whatsapp.WhatsappResponsiblePanel";

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.store = useService("mail.store");
        this.state = useState({ users: [], loading: true, saving: false });
        onMounted(() => this.loadUsers());
    }

    get currentId() {
        return this.props.thread.whatsappResponsibleId || false;
    }

    get canRelease() {
        return Boolean(this.currentId) && this.state.users.some((user) => user.id === this.currentId);
    }

    async loadUsers() {
        this.state.loading = true;
        try {
            this.state.users = await this.orm.call(
                "discuss.channel",
                "whatsapp_get_assignable_users",
                [[this.props.thread.id]]
            );
        } finally {
            this.state.loading = false;
        }
    }

    async assign(userId) {
        this.state.saving = true;
        try {
            const data = await this.orm.call(
                "discuss.channel",
                "whatsapp_set_responsible",
                [[this.props.thread.id], userId]
            );
            this.store.insert(data);
            const user = this.state.users.find((item) => item.id === userId);
            this.props.thread.whatsappResponsibleId = userId || false;
            this.props.thread.whatsappResponsibleName = user?.name || false;
        } catch (error) {
            this.notification.add(
                error?.data?.message || _t("Could not change the responsible."),
                { type: "danger" }
            );
        } finally {
            this.state.saving = false;
        }
    }
}
