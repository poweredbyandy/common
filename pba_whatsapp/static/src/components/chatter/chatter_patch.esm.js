import {Chatter} from "@mail/chatter/web_portal/chatter";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";
import {onWillStart, useState} from "@odoo/owl";

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.whatsappState = useState({
            mode: "message",
            templates: [],
            selectedTemplateId: false,
        });
        onWillStart(async () => {
            this.whatsappState.templates = await this.orm.searchRead(
                "mail.whatsapp.template",
                [["state", "=", "approved"], ["is_supported", "=", true]],
                ["name", "body"]
            );
        });
    },
    onClickWhatsapp() {
        const thread = this.state.thread;
        if (!thread?.id) {
            this.onThreadCreated = () => this.onClickWhatsapp();
            this.props.saveRecord?.();
            return;
        }
        this.orm
            .call(thread.model, "action_pba_whatsapp_get_gateway_notification", [
                [thread.id],
            ])
            .then((notif) => {
                if (thread.gateway_notifications) {
                    thread.gateway_notifications = [];
                }
                thread.gateway_notifications = [notif];
                this.toggleComposer("gateway");
            })
            .catch(() => {
                this.toggleComposer("gateway");
            });
    },
    onWhatsappModeChange(ev) {
        this.whatsappState.mode = ev.target.value;
        this.whatsappState.selectedTemplateId = false;
        if (this.whatsappState.mode === "message") {
            const composer = this.state.thread?.composer;
            if (composer) {
                composer.textInputContent = "";
            }
        }
    },
    onWhatsappTemplateChange(ev) {
        const templateId = Number(ev.target.value);
        this.whatsappState.selectedTemplateId = templateId || false;
        const template = this.whatsappState.templates.find((item) => item.id === templateId);
        const composer = this.state.thread?.composer;
        if (template && composer) {
            composer.textInputContent = template.body || "";
        }
    },
});
