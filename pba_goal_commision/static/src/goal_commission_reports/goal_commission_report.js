/** @odoo-module **/

import { registry } from "@web/core/registry";
import { downloadFile } from "@web/core/network/download";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";
import { KeepLast } from "@web/core/utils/concurrency";

const REPORT_CONFIG = {
    seller_sale: {
        title: "Ventas por vendedor",
        loadMethod: "get_seller_sale_report",
        showCollectedFilter: true,
        showMinDaysFilter: false,
    },
    late_payment: {
        title: "Facturas pagadas tardías",
        loadMethod: "get_late_payment_report",
        showCollectedFilter: false,
        showMinDaysFilter: false,
    },
    pending_commission: {
        title: "Comisiones pendientes de pago",
        loadMethod: "get_pending_commission_report",
        showCollectedFilter: false,
        showMinDaysFilter: true,
    },
};

export class GoalCommissionReportBase extends Component {
    static template = "pba_goal_commision.GoalCommissionReport";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");
        this.keepLast = new KeepLast();
        this.config = REPORT_CONFIG[this.constructor.reportType];
        this.state = useState({
            loading: true,
            exporting: false,
            filters: {
                period_id: "",
                seller_partner_id: "",
                collected: "all",
                min_days: "0",
            },
            filterOptions: { periods: [], sellers: [], is_admin: false, default_period_id: false },
            lines: [],
            summary_by_seller: [],
            totals: {},
        });
        onWillStart(async () => {
            await this.loadFilterOptions();
            await this.loadReport();
        });
    }

    get reportType() {
        return this.constructor.reportType;
    }

    async loadFilterOptions() {
        const options = await this.orm.call(
            "goal.commission.report.service",
            "get_report_filters",
            []
        );
        this.state.filterOptions = options;
        if (options.default_period_id && !this.state.filters.period_id) {
            this.state.filters.period_id = options.default_period_id;
        }
    }

    _reportPayload() {
        const periodId = Number(this.state.filters.period_id);
        const sellerId = Number(this.state.filters.seller_partner_id);
        return {
            period_id: periodId || false,
            seller_partner_id: sellerId || false,
            collected: this.state.filters.collected,
            min_days: Number(this.state.filters.min_days) || 0,
        };
    }

    async loadReport() {
        this.state.loading = true;
        const data = await this.keepLast.add(
            this.orm.call("goal.commission.report.service", this.config.loadMethod, [], {
                filters: this._reportPayload(),
            })
        );
        this.state.lines = data.lines || [];
        this.state.summary_by_seller = data.summary_by_seller || [];
        this.state.totals = data.totals || {};
        this.state.loading = false;
    }

    async onFilterChange() {
        await this.loadReport();
    }

    formatAmount(value) {
        return Number(value || 0).toLocaleString(undefined, {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        });
    }

    formatDate(value) {
        if (!value) {
            return "—";
        }
        return value;
    }

    async openInvoice(invoiceId) {
        if (!invoiceId) {
            return;
        }
        await this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "account.move",
            res_id: invoiceId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    _decodeBase64(base64Content) {
        const binary = atob(base64Content);
        const bytes = new Uint8Array(binary.length);
        for (let index = 0; index < binary.length; index++) {
            bytes[index] = binary.charCodeAt(index);
        }
        return bytes.buffer;
    }

    async downloadExcel() {
        if (!this.state.lines.length || this.state.exporting) {
            return;
        }
        this.state.exporting = true;
        try {
            const result = await this.orm.call(
                "goal.commission.report.service",
                "export_report_excel",
                [this.reportType],
                { filters: this._reportPayload() }
            );
            const data = this._decodeBase64(result.file_content);
            await downloadFile(
                data,
                result.file_name,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            );
            this.notification.add("Excel descargado correctamente.", { type: "success" });
        } catch (error) {
            this.notification.add(error.message || "No se pudo exportar el reporte.", {
                type: "danger",
            });
        } finally {
            this.state.exporting = false;
        }
    }
}

export class GoalCommissionSellerSaleReport extends GoalCommissionReportBase {
    static reportType = "seller_sale";
}

export class GoalCommissionLatePaymentReport extends GoalCommissionReportBase {
    static reportType = "late_payment";
}

export class GoalCommissionPendingCommissionReport extends GoalCommissionReportBase {
    static reportType = "pending_commission";
}

registry.category("actions").add(
    "goal_commission_report_seller_sale",
    GoalCommissionSellerSaleReport
);
registry.category("actions").add(
    "goal_commission_report_late_payment",
    GoalCommissionLatePaymentReport
);
registry.category("actions").add(
    "goal_commission_report_pending_commission",
    GoalCommissionPendingCommissionReport
);
