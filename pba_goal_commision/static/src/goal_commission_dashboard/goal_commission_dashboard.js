/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, markup, onWillStart, useState } from "@odoo/owl";
import { KeepLast } from "@web/core/utils/concurrency";

export class GoalCommissionSellerDashboard extends Component {
    static template = "pba_goal_commision.GoalCommissionSellerDashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.keepLast = new KeepLast();
        this.state = useState({
            loading: true,
            periodId: false,
            periodName: "",
            periods: [],
            sellers: [],
        });
        onWillStart(async () => {
            await this.loadDashboard();
        });
    }

    _periodContext() {
        return {
            goal_commission_period_id: Number(this.state.periodId) || false,
        };
    }

    _prepareSellers(sellers) {
        return (sellers || []).map((seller) => ({
            ...seller,
            tier_badges_html: markup(seller.tier_badges_html || ""),
        }));
    }

    async loadDashboard() {
        this.state.loading = true;
        const data = await this.keepLast.add(
            this.orm.call("res.partner", "get_goal_commission_dashboard_data", [], {
                period_id: Number(this.state.periodId) || false,
            })
        );
        this.state.periods = data.periods || [];
        this.state.periodId = data.period_id || false;
        this.state.periodName = data.period_name || "";
        this.state.sellers = this._prepareSellers(data.sellers);
        this.state.loading = false;
    }

    get periodIndex() {
        return this.state.periods.findIndex((period) => period.id === this.state.periodId);
    }

    get canOlderPeriod() {
        return this.periodIndex > -1 && this.periodIndex < this.state.periods.length - 1;
    }

    get canNewerPeriod() {
        return this.periodIndex > 0;
    }

    async onPeriodChange() {
        await this.loadDashboard();
    }

    async goOlderPeriod() {
        if (!this.canOlderPeriod) {
            return;
        }
        this.state.periodId = this.state.periods[this.periodIndex + 1].id;
        await this.loadDashboard();
    }

    async goNewerPeriod() {
        if (!this.canNewerPeriod) {
            return;
        }
        this.state.periodId = this.state.periods[this.periodIndex - 1].id;
        await this.loadDashboard();
    }

    async openSeller(sellerId) {
        if (!sellerId) {
            return;
        }
        await this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "res.partner",
            res_id: sellerId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    async openPending(ev, sellerId) {
        ev.stopPropagation();
        await this.actionService.doActionButton({
            type: "object",
            resModel: "res.partner",
            name: "action_open_goal_pending_commissions",
            resId: sellerId,
            context: this._periodContext(),
        });
    }

    async payCommissions(ev, sellerId) {
        ev.stopPropagation();
        await this.actionService.doActionButton({
            type: "object",
            resModel: "res.partner",
            name: "action_pay_goal_pending_commissions",
            resId: sellerId,
            context: this._periodContext(),
            onClose: () => this.loadDashboard(),
        });
    }
}

registry.category("actions").add(
    "goal_commission_seller_dashboard",
    GoalCommissionSellerDashboard
);
