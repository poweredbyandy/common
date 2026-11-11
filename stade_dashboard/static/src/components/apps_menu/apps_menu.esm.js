/* global document, location, window */

/* Copyright 2018 Tecnativa - Jairo Llopis
 * Copyright 2021 ITerra - Sergey Shebanin
 * Copyright 2023 Onestein - Anjeel Haria
 * Copyright 2023 Taras Shabaranskyi
 * Copyright 2026 andyengit
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */

import {Component, onWillStart, useState} from "@odoo/owl";
import {useBus, useService} from "@web/core/utils/hooks";
import {AppMenuItem} from "@stade_dashboard/components/apps_menu_item/apps_menu_item.esm";
import {AppsMenuSearchBar} from "@stade_dashboard/components/menu_searchbar/searchbar.esm";
import {HomeDashboard} from "@stade_dashboard/components/home_dashboard/home_dashboard.esm";
import {NavBar} from "@web/webclient/navbar/navbar";
import {WebClient} from "@web/webclient/webclient";
import {browser} from "@web/core/browser/browser";
import {patch} from "@web/core/utils/patch";
import {router} from "@web/core/browser/router";
import {session} from "@web/session";
import {useHotkey} from "@web/core/hotkeys/hotkey_hook";
import {user} from "@web/core/user";
import {BurgerMenu} from "@web/webclient/burger_menu/burger_menu";

function hasRouterAction(route) {
    if (!route) {
        return false;
    }
    if (Number(route.menu_id || 0)) {
        return true;
    }
    if (route.model) {
        return true;
    }
    if (route.action && route.action !== "menu") {
        return true;
    }
    return (route.actionStack || []).some(
        (entry) => entry.model || (entry.action && entry.action !== "menu")
    );
}

patch(WebClient.prototype, {
    setup() {
        super.setup();
        useBus(this.env.bus, "APPS_MENU:STATE_CHANGED", ({detail: state}) => {
            document.body.classList.toggle("o_apps_menu_opened", state);
        });
        this.user = user;
        onWillStart(async () => {
            const is_redirect_home = await this.orm.searchRead(
                "res.users",
                [["id", "=", this.user.userId]],
                ["is_redirect_home"]
            );
            user.updateContext({
                is_redirect_to_home: is_redirect_home[0]?.is_redirect_home,
            });
        });
        this.redirect = false;
    },
    _loadDefaultApp() {
        if (user.context.is_redirect_to_home) {
            this.env.bus.trigger("APPS_MENU:STATE_CHANGED", true);
        } else {
            super._loadDefaultApp();
        }
    },
});

export class AppsMenu extends Component {
    setup() {
        super.setup();
        this.router = router;
        this.theme = session.apps_menu.theme || "milk";
        this.menuService = useService("menu");
        browser.localStorage.setItem("redirect_menuId", "");
        const openHome =
            Boolean(user.context.is_redirect_to_home) &&
            !hasRouterAction(this.router.current);
        this.state = useState({open: openHome});
        useBus(this.env.bus, "APPS_MENU:STATE_CHANGED", ({detail: openState}) => {
            this.state.open = Boolean(openState);
        });
        if (openHome) {
            this.env.bus.trigger("APPS_MENU:STATE_CHANGED", true);
        }
        useBus(this.env.bus, "ACTION_MANAGER:UI-UPDATED", () => {
            if (hasRouterAction(this.router.current)) {
                this.setOpenState(false);
            }
        });
        this._setupKeyNavigation();
    }

    setOpenState(open_state) {
        this.state.open = open_state;
        this.env.bus.trigger("APPS_MENU:STATE_CHANGED", open_state);
    }

    _setupKeyNavigation() {
        const repeatable = {
            allowRepeat: true,
        };
        useHotkey(
            "ArrowRight",
            () => {
                this._onWindowKeydown("next");
            },
            repeatable
        );
        useHotkey(
            "ArrowLeft",
            () => {
                this._onWindowKeydown("prev");
            },
            repeatable
        );
        useHotkey(
            "ArrowDown",
            () => {
                this._onWindowKeydown("next");
            },
            repeatable
        );
        useHotkey(
            "ArrowUp",
            () => {
                this._onWindowKeydown("prev");
            },
            repeatable
        );
        useHotkey("Escape", () => {
            this.env.bus.trigger("ACTION_MANAGER:UI-UPDATED");
        });
    }

    _onWindowKeydown(direction) {
        const focusableInputElements = document.querySelectorAll(".o-app-menu-item");
        if (focusableInputElements.length) {
            const focusable = [...focusableInputElements];
            const index = focusable.indexOf(document.activeElement);
            let nextIndex = 0;
            if (direction === "prev" && index >= 0) {
                if (index > 0) {
                    nextIndex = index - 1;
                } else {
                    nextIndex = focusable.length - 1;
                }
            } else if (direction === "next") {
                if (index + 1 < focusable.length) {
                    nextIndex = index + 1;
                } else {
                    nextIndex = 0;
                }
            }
            focusableInputElements[nextIndex].focus();
        }
    }

    onMenuClick() {
        const onPortal = this.state.open && !hasRouterAction(this.router.current);
        if (onPortal) {
            this.setOpenState(false);
            this.env.bus.trigger("APP_MENU:OPEN_APP_SECTIONS");
            return;
        }
        this.env.bus.trigger("APP_MENU:CLOSE_APP_SECTIONS");
        this.setOpenState(!this.state.open);
    }
}

patch(NavBar.prototype, {
    setup() {
        super.setup();

        useBus(this.env.bus, "APP_MENU:TOGGLE_SIDEBAR", () => {
            this._openAppMenuSidebar();
        });
        useBus(this.env.bus, "APP_MENU:OPEN_APP_SECTIONS", () => {
            this._openAppSections();
        });
        useBus(this.env.bus, "APP_MENU:CLOSE_APP_SECTIONS", () => {
            this._closeAppMenuSidebar();
        });
    },

    _openAppSections() {
        if (this.state.isAppMenuSidebarOpened && !this.state.isAllAppsMenuOpened) {
            this._closeAppMenuSidebar();
            return;
        }
        if (!this.menuService.getCurrentApp()) {
            const stored =
                browser.sessionStorage.getItem("menu_id") ||
                browser.localStorage.getItem("redirect_menuId");
            const menuId = Number(stored);
            const menu = menuId && this.menuService.getMenu(menuId);
            if (menu) {
                this.menuService.setCurrentMenu(menu);
            } else {
                const [firstApp] = this.menuService.getApps();
                if (firstApp) {
                    this.menuService.setCurrentMenu(firstApp);
                }
            }
        }
        this.state.isAllAppsMenuOpened = false;
        this.state.isAppMenuSidebarOpened = true;
    },

    openAppMenu() {
        this.env.bus.trigger("APP_MENU:OPEN_APP_MENU");
        this._closeAppMenuSidebar();
    },
});

Object.assign(AppsMenu, {
    template: "stade_dashboard.AppsMenu",
    props: {
        slots: {
            type: Object,
            optional: true,
        },
    },
});

Object.assign(NavBar.components, {
    AppsMenu,
    AppMenuItem,
    AppsMenuSearchBar,
    HomeDashboard,
});

patch(BurgerMenu.prototype, {
    setup() {
        super.setup();
    },

    _openAppMenuSidebarMobile() {
        this.env.bus.trigger("APP_MENU:TOGGLE_SIDEBAR");
    },
});
