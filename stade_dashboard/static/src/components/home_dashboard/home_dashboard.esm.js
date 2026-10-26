/* Copyright 2026 andyengit
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */

import {Component, onWillStart, useState} from "@odoo/owl";
import {useService} from "@web/core/utils/hooks";
import {user} from "@web/core/user";
import {_t} from "@web/core/l10n/translation";

export class HomeDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            activities: [],
            loadingActivities: true,
        });
        onWillStart(async () => {
            await this.loadActivities();
        });
    }

    async loadActivities() {
        this.state.loadingActivities = true;
        try {
            this.state.activities = await this.orm.searchRead(
                "mail.activity",
                [["user_id", "=", user.userId]],
                [
                    "res_name",
                    "summary",
                    "date_deadline",
                    "activity_type_id",
                    "res_model",
                    "res_id",
                    "state",
                    "icon",
                ],
                {order: "date_deadline asc, id asc", limit: 10}
            );
        } catch {
            this.state.activities = [];
        } finally {
            this.state.loadingActivities = false;
        }
    }

    async openActivity(activity) {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: activity.res_model,
            res_id: activity.res_id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openAllActivities() {
        this.action.doAction("mail.mail_activity_action_my", {
            clearBreadcrumbs: true,
        });
    }

    activityLabel(activity) {
        return activity.summary || activity.res_name || _t("Activity");
    }

    stateClass(state) {
        if (state === "overdue") {
            return "text-danger";
        }
        if (state === "today") {
            return "text-warning";
        }
        return "text-muted";
    }
}

Object.assign(HomeDashboard, {
    template: "stade_dashboard.HomeDashboard",
    props: {},
});
