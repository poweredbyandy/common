/* Copyright 2023 Taras Shabaranskyi
 * Copyright 2026 andyengit
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */

import {_t} from "@web/core/l10n/translation";
import {registry} from "@web/core/registry";
import {user} from "@web/core/user";

function appsMenuPreferencesItem(env) {
    return {
        type: "item",
        id: "apps_menu_preferences",
        description: _t("App Menu Preferences"),
        callback: async () => {
            const onClose = () => env.services.action.doAction("reload_context");
            const action = await env.services.action.loadAction(
                "stade_dashboard.res_users_view_form_apps_menu_preferences_action"
            );
            env.services.action.doAction({...action, res_id: user.userId}, {onClose});
        },
        sequence: 55,
    };
}

registry.category("user_menuitems").add("apps_menu_preferences", appsMenuPreferencesItem);
