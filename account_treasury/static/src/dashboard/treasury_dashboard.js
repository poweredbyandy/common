import { Component, onWillStart, useEffect, useRef, useState } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { formatMonetary } from "@web/views/fields/formatters";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";

const { DateTime, Info } = luxon;

const INFLOW_COLOR = "#28a745";
const OUTFLOW_COLOR = "#dc3545";
const BALANCE_COLOR = "#017e84";
const REAL_BALANCE_COLOR = "#714b67";
const GRID_COLOR = "rgba(128, 128, 128, 0.2)";

export class TreasuryDashboard extends Component {
    static template = "account_treasury.TreasuryDashboard";
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.canvasRef = useRef("chart");
        this.chart = null;
        this.state = useState({
            mode: "month",
            anchor: DateTime.local().startOf("month"),
            currencyId: false,
            rateMode: "document",
            data: null,
        });
        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            await this.load();
        });
        useEffect(
            () => {
                this.renderChart();
                return () => this.chart?.destroy();
            },
            () => [this.state.data]
        );
    }

    get rateModes() {
        return [
            { value: "document", label: _t("Document date rate") },
            { value: "today", label: _t("Today's rate") },
        ];
    }

    get periodLabel() {
        const format = this.state.mode === "month" ? "LLLL yyyy" : "yyyy";
        return this.state.anchor.toFormat(format);
    }

    get weekdays() {
        return Info.weekdays("short");
    }

    get bucketsByKey() {
        return Object.fromEntries((this.state.data?.buckets || []).map((b) => [b.key, b]));
    }

    get weeks() {
        const anchor = this.state.anchor;
        const buckets = this.bucketsByKey;
        const items = this.state.data?.items || {};
        const today = this.state.data?.today;
        const end = anchor.endOf("month").endOf("week");
        const weeks = [];
        let cursor = anchor.startOf("month").startOf("week");
        while (cursor <= end) {
            const week = [];
            for (let index = 0; index < 7; index++) {
                const key = cursor.toISODate();
                week.push({
                    key,
                    number: cursor.day,
                    inMonth: cursor.month === anchor.month,
                    isToday: key === today,
                    isPast: key < today,
                    bucket: buckets[key],
                    items: (items[key] || []).filter(
                        (item) => item.kind === "real" || item.state !== "done"
                    ),
                });
                cursor = cursor.plus({ days: 1 });
            }
            weeks.push(week);
        }
        return weeks;
    }

    get months() {
        return (this.state.data?.buckets || []).map((bucket) => ({
            ...bucket,
            label: DateTime.fromISO(`${bucket.key}-01`).toFormat("LLLL"),
            isCurrent: bucket.key === this.state.data.today.slice(0, 7),
        }));
    }

    get totals() {
        return this.state.data?.totals || {};
    }

    getRange() {
        const unit = this.state.mode === "month" ? "month" : "year";
        return {
            dateFrom: this.state.anchor.startOf(unit).toISODate(),
            dateTo: this.state.anchor.endOf(unit).toISODate(),
            groupBy: this.state.mode === "month" ? "day" : "month",
        };
    }

    async load() {
        const { dateFrom, dateTo, groupBy } = this.getRange();
        const data = await this.orm.call("account.treasury.dashboard", "get_dashboard_data", [
            dateFrom,
            dateTo,
            this.state.currencyId,
            this.state.rateMode,
            groupBy,
        ]);
        this.state.currencyId = data.currency_id;
        this.state.data = data;
    }

    format(value) {
        return formatMonetary(value, { currencyId: this.state.currencyId });
    }

    isOverdue(item, day) {
        return item.kind === "forecast" && day.isPast && ["pending", "partial"].includes(item.state);
    }

    itemIcon(item, day) {
        if (item.kind === "real") {
            return "fa-money";
        }
        if (this.isOverdue(item, day)) {
            return "fa-exclamation-triangle";
        }
        return {
            pending: "fa-clock-o",
            partial: "fa-adjust",
            done: "fa-check",
        }[item.state];
    }

    itemTitle(item) {
        const parts = [item.name, item.partner, item.category, item.reference];
        if (item.kind === "forecast" && item.state !== "done") {
            parts.push(_t("Due: %s", this.format(item.residual)));
        }
        return parts.filter(Boolean).join(" - ");
    }

    async onChangeMode(mode) {
        this.state.mode = mode;
        await this.load();
    }

    async onNavigate(step) {
        const unit = this.state.mode === "month" ? "months" : "years";
        this.state.anchor = step
            ? this.state.anchor.plus({ [unit]: step })
            : DateTime.local().startOf("month");
        await this.load();
    }

    async onChangeCurrency(ev) {
        this.state.currencyId = parseInt(ev.target.value);
        await this.load();
    }

    async onChangeRateMode(ev) {
        this.state.rateMode = ev.target.value;
        await this.load();
    }

    async onOpenMonth(bucket) {
        this.state.anchor = DateTime.fromISO(`${bucket.key}-01`);
        this.state.mode = "month";
        await this.load();
    }

    openForecast(forecastId) {
        this.action.doAction(
            {
                type: "ir.actions.act_window",
                name: _t("Forecast"),
                res_model: "account.treasury.forecast",
                res_id: forecastId,
                views: [[false, "form"]],
                target: "new",
            },
            { onClose: () => this.load() }
        );
    }

    createForecast(day) {
        this.action.doAction(
            {
                type: "ir.actions.act_window",
                name: _t("New Forecast"),
                res_model: "account.treasury.forecast",
                views: [[false, "form"]],
                target: "new",
                context: { default_date: day.key },
            },
            { onClose: () => this.load() }
        );
    }

    chartLabel(key) {
        return this.state.mode === "month"
            ? DateTime.fromISO(key).toFormat("d")
            : DateTime.fromISO(`${key}-01`).toFormat("LLL");
    }

    renderChart() {
        if (!this.canvasRef.el || !this.state.data) {
            return;
        }
        this.chart?.destroy();
        const buckets = this.state.data.buckets;
        const series = (name, sign = 1) => buckets.map((bucket) => sign * bucket[name]);
        const dataset = (label, data, color, stack, alpha = 1) => ({
            type: "bar",
            label,
            data,
            stack,
            backgroundColor: alpha === 1 ? color : `${color}66`,
            borderColor: color,
            borderWidth: 1,
            order: 2,
        });
        this.chart = new Chart(this.canvasRef.el, {
            type: "bar",
            data: {
                labels: buckets.map((bucket) => this.chartLabel(bucket.key)),
                datasets: [
                    {
                        type: "line",
                        label: _t("Projected balance"),
                        data: series("balance"),
                        borderColor: BALANCE_COLOR,
                        backgroundColor: BALANCE_COLOR,
                        borderWidth: 2,
                        pointRadius: 2,
                        tension: 0.2,
                        order: 1,
                    },
                    {
                        type: "line",
                        label: _t("Real balance"),
                        data: series("real_balance"),
                        borderColor: REAL_BALANCE_COLOR,
                        backgroundColor: REAL_BALANCE_COLOR,
                        borderDash: [6, 4],
                        borderWidth: 2,
                        pointRadius: 2,
                        tension: 0.2,
                        order: 0,
                    },
                    dataset(_t("Real inflows"), series("real_in"), INFLOW_COLOR, "in"),
                    dataset(_t("Pending inflows"), series("pending_in"), INFLOW_COLOR, "in", 0.4),
                    dataset(_t("Real outflows"), series("real_out", -1), OUTFLOW_COLOR, "out"),
                    dataset(
                        _t("Pending outflows"),
                        series("pending_out", -1),
                        OUTFLOW_COLOR,
                        "out",
                        0.4
                    ),
                ],
            },
            options: {
                maintainAspectRatio: false,
                interaction: { mode: "index", intersect: false },
                scales: {
                    x: { stacked: true, grid: { display: false } },
                    y: {
                        stacked: true,
                        ticks: { callback: (value) => this.format(value) },
                        grid: { color: GRID_COLOR },
                    },
                },
                plugins: {
                    legend: { position: "bottom" },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => `${ctx.dataset.label}: ${this.format(ctx.parsed.y)}`,
                        },
                    },
                },
            },
        });
    }
}

registry.category("actions").add("account_treasury.dashboard", TreasuryDashboard);
