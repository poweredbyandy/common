import {AppsMenu} from "@web_responsive/components/apps_menu/apps_menu.esm";
import {WebClient} from "@web/webclient/webclient";
import {browser} from "@web/core/browser/browser";
import {patch} from "@web/core/utils/patch";

const OPEN_APPS_MENU_STORAGE_KEY = "web_responsive_open_apps_menu";

function hasOpenAppsMenuFlag() {
    return browser.sessionStorage.getItem(OPEN_APPS_MENU_STORAGE_KEY) === "1";
}

function consumeOpenAppsMenuFlag() {
    if (!hasOpenAppsMenuFlag()) {
        return false;
    }
    browser.sessionStorage.removeItem(OPEN_APPS_MENU_STORAGE_KEY);
    return true;
}

patch(WebClient.prototype, {
    async loadRouterState() {
        if (hasOpenAppsMenuFlag()) {
            browser.sessionStorage.removeItem("menu_id");
        }
        return super.loadRouterState(...arguments);
    },
    _loadDefaultApp() {
        if (consumeOpenAppsMenuFlag()) {
            this.env.bus.trigger("APPS_MENU:STATE_CHANGED", true);
            return;
        }
        return super._loadDefaultApp();
    },
});

patch(AppsMenu.prototype, {
    setup() {
        super.setup();
        if (hasOpenAppsMenuFlag()) {
            this.state.open = true;
            this.env.bus.trigger("APPS_MENU:STATE_CHANGED", true);
        }
    },
});
