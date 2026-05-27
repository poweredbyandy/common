import {Chatter} from "@mail/chatter/web_portal/chatter";
import {patch} from "@web/core/utils/patch";
import {useService} from "@web/core/utils/hooks";

patch(Chatter.prototype, {
    setup() {
        super.setup(...arguments);
        this.action = useService("action");
    },
    async onClickWhatsapp() {
        const thread = this.state.thread;
        if (!thread?.id) {
            this.onThreadCreated = () => this.onClickWhatsapp();
            this.props.saveRecord?.();
            return;
        }
        const action = await this.orm.call(
            thread.model,
            "action_open_whatsapp_composer",
            [[thread.id]]
        );
        if (action) {
            await this.action.doAction(action);
        }
    },
});
