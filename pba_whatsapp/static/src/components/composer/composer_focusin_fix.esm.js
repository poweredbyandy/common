import {Composer} from "@mail/core/common/composer";
import {patch} from "@web/core/utils/patch";

patch(Composer.prototype, {
    onFocusin(ev) {
        if (ev?.stopPropagation) {
            ev.stopPropagation();
        }
        this.props.composer.isFocused = true;
        this.thread?.markAsRead();
        if (this.props.type !== "gateway" && this.thread) {
            this.thread.gateway_notifications = [];
        }
    },
});
