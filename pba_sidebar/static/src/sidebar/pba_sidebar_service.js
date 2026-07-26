/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { reactive } from "@odoo/owl";
import { computeAppsAndMenuItems, reorderApps } from "@web/webclient/menus/menu_helpers";
import { router } from "@web/core/browser/router";

const HISTORY_LIMIT = 40;
const OPEN_STORAGE_KEY = "pba_sidebar.is_open";

function historyStorageKey() {
    return `pba_sidebar.history.${user.userId}`;
}

function loadHistory() {
    try {
        const raw = browser.localStorage.getItem(historyStorageKey());
        return raw ? JSON.parse(raw) : [];
    } catch {
        return [];
    }
}

function saveHistory(history) {
    browser.localStorage.setItem(historyStorageKey(), JSON.stringify(history));
}

function loadIsOpen() {
    const stored = browser.localStorage.getItem(OPEN_STORAGE_KEY);
    return stored === null ? true : stored === "true";
}

function serializeContext(context = {}) {
    const ignored = new Set([
        "lang",
        "tz",
        "uid",
        "allowed_company_ids",
        "bin_size",
        "current_company_id",
    ]);
    const result = {};
    for (const [key, value] of Object.entries(context)) {
        if (ignored.has(key) || value === undefined || value === null || value === false) {
            continue;
        }
        if (typeof value === "object") {
            continue;
        }
        result[key] = value;
    }
    return result;
}

function buildHistoryEntry(env) {
    const controller = env.services.action.currentController;
    if (!controller?.action) {
        return null;
    }
    const action = controller.action;
    if (action.tag === "menu" || action.target === "new") {
        return null;
    }
    const app = env.services.menu.getCurrentApp();
    const props = controller.props || {};
    const route = router.current || {};
    const resId = props.resId || route.resId || false;
    const model = props.resModel || action.res_model || route.model || false;
    const viewType = controller.view?.type || props.type || route.view_type || false;
    const context = serializeContext(action.context || {});
    const breadcrumbs = (controller.config?.breadcrumbs || []).map((item) => item.name).filter(Boolean);
    const href = `${browser.location.pathname}${browser.location.search}${browser.location.hash}`;
    const displayName = controller.displayName || action.display_name || action.name || "";
    return {
        id: `${action.id || action.tag || "action"}:${model || ""}:${resId || ""}:${viewType || ""}:${href}`,
        displayName,
        actionId: action.id || false,
        actionPath: action.path || false,
        actionType: action.type,
        model,
        resId: resId === "new" ? false : resId,
        viewType,
        context,
        breadcrumbs,
        appName: app?.name || "",
        appXmlid: app?.xmlid || "",
        href,
        timestamp: Date.now(),
    };
}

function isSameEntry(a, b) {
    return a && b && a.id === b.id;
}

export const pbaSidebarService = {
    dependencies: ["menu", "action"],
    start(env) {
        const state = reactive({
            isOpen: loadIsOpen(),
            isReordering: false,
            apps: [],
            history: loadHistory(),
        });

        function refreshApps() {
            const apps = computeAppsAndMenuItems(env.services.menu.getMenuAsTree("root")).apps;
            const order = user.settings?.pba_sidebar_app_order;
            if (Array.isArray(order) && order.length) {
                reorderApps(apps, order);
            }
            state.apps.splice(0, state.apps.length, ...apps);
        }

        function setOpen(isOpen) {
            state.isOpen = Boolean(isOpen);
            browser.localStorage.setItem(OPEN_STORAGE_KEY, String(state.isOpen));
            document.body.classList.toggle("o_pba_sidebar_open", state.isOpen && !env.isSmall);
        }

        function toggle() {
            setOpen(!state.isOpen);
        }

        function recordHistory() {
            if (env.isSmall) {
                return;
            }
            const entry = buildHistoryEntry(env);
            if (!entry || !entry.displayName) {
                return;
            }
            if (isSameEntry(state.history[0], entry)) {
                Object.assign(state.history[0], entry);
                saveHistory(state.history);
                return;
            }
            state.history.unshift(entry);
            if (state.history.length > HISTORY_LIMIT) {
                state.history.splice(HISTORY_LIMIT);
            }
            saveHistory(state.history);
        }

        async function openApp(app) {
            await env.services.menu.selectMenu(app.id);
        }

        async function openHistoryEntry(entry) {
            if (!entry?.actionId) {
                return;
            }
            const options = {
                additionalContext: entry.context || {},
                clearBreadcrumbs: true,
            };
            if (entry.resId) {
                options.viewType = entry.viewType || "form";
                options.props = { resId: entry.resId };
            } else if (entry.viewType) {
                options.viewType = entry.viewType;
            }
            await env.services.action.doAction(entry.actionId, options);
        }

        function clearHistory() {
            state.history.splice(0, state.history.length);
            saveHistory(state.history);
        }

        function setReordering(value) {
            state.isReordering = Boolean(value);
        }

        async function saveAppOrder(order) {
            reorderApps(state.apps, order);
            await user.setUserSettings("pba_sidebar_app_order", order);
        }

        refreshApps();
        setOpen(state.isOpen);

        env.bus.addEventListener("MENUS:APP-CHANGED", refreshApps);
        env.bus.addEventListener("ACTION_MANAGER:UI-UPDATED", recordHistory);

        return {
            state,
            toggle,
            setOpen,
            refreshApps,
            openApp,
            openHistoryEntry,
            clearHistory,
            setReordering,
            saveAppOrder,
        };
    },
};

registry.category("services").add("pba_sidebar", pbaSidebarService);
