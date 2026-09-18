import {AppsMenu} from "@web_responsive/components/apps_menu/apps_menu.esm";
import {patch} from "@web/core/utils/patch";
import {session} from "@web/session";

patch(AppsMenu.prototype, {
    setup() {
        super.setup();
        this.appsMenuBackground = session.apps_menu_background || {};
    },
    get backgroundUrl() {
        return this.appsMenuBackground.url || "";
    },
    get backgroundStyle() {
        const background = this.appsMenuBackground;
        if (!background.url) {
            return "";
        }
        return [
            `--o-apps-menu-bg-image: url("${background.url}")`,
            `--o-apps-menu-bg-size: ${background.size}% auto`,
            `--o-apps-menu-bg-position: ${background.position}`,
            `--o-apps-menu-bg-opacity: ${background.opacity}`,
        ].join("; ");
    },
});
