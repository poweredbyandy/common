import { Message as MessageModel } from "@mail/core/common/message_model";
import { Message } from "@mail/core/common/message";
import { patch } from "@web/core/utils/patch";

patch(MessageModel.prototype, {
    /** @type {number|false} */
    sub_user_id: false,
    /** @type {string|false} */
    sub_user_name: false,
});

patch(Message.prototype, {
    get authorName() {
        const name = super.authorName;
        if (this.message.sub_user_name) {
            return name + " - " + this.message.sub_user_name;
        }
        return name;
    },
});
