import {Composer} from "@mail/core/common/composer";
import {_t} from "@web/core/l10n/translation";
import {patch} from "@web/core/utils/patch";

patch(Composer.prototype, {
    get SEND_TEXT() {
        if (this.props.type === "gateway" && !this.props.composer.message) {
            return _t("Enviar WhatsApp");
        }
        return super.SEND_TEXT;
    },
    get placeholder() {
        if (
            this.thread?.model !== "discuss.channel" &&
            !this.props.placeholder &&
            this.props.type === "gateway"
        ) {
            return _t("Escribe un mensaje de WhatsApp...");
        }
        return super.placeholder;
    },
});
