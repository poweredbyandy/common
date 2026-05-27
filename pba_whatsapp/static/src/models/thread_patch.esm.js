import {Thread} from "@mail/core/common/thread_model";
import {patch} from "@web/core/utils/patch";

patch(Thread.prototype, {
    update(data) {
        super.update(data);
        if (this.channel_type === "gateway" && "operator" in data) {
            this.operator = data.operator;
        }
        if (this.channel_type === "gateway" && "crm_seller" in data) {
            this.crm_seller = data.crm_seller;
        }
    },
});
