import {assignIn} from "@mail/utils/common/misc";
import {Thread} from "@mail/core/common/thread_model";
import {patch} from "@web/core/utils/patch";

patch(Thread, {
    _insert(data) {
        const thread = super._insert(...arguments);
        if (thread.channel_type === "gateway" || thread.type === "gateway") {
            assignIn(thread, data, ["whatsapp_crm_lead_count", "crm_seller"]);
        }
        return thread;
    },
});

patch(Thread.prototype, {
    setup() {
        super.setup();
        this.whatsapp_crm_lead_count = 0;
    },
    update(data) {
        super.update(data);
        if (this.channel_type === "gateway") {
            if ("whatsapp_crm_lead_count" in data) {
                this.whatsapp_crm_lead_count = data.whatsapp_crm_lead_count;
            }
            if ("crm_seller" in data) {
                this.crm_seller = data.crm_seller || undefined;
            }
        }
    },
});
