/** @odoo-module **/

import { Component, markup, onWillStart, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { Layout } from "@web/search/layout";

const STATE_LABELS = {
    pending_approval: _t("Pendiente de aprobación"),
    submitted: _t("Enviado"),
    in_progress: _t("En progreso"),
    resolved: _t("Resuelto"),
    cancelled: _t("Cancelado"),
};

const PRIORITY_LABELS = {
    "0": _t("Baja"),
    "1": _t("Normal"),
    "2": _t("Alta"),
    "3": _t("Urgente"),
};

const MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024;

function fileToBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
            const result = reader.result || "";
            const base64 = String(result).split(",")[1] || "";
            resolve(base64);
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

export class PbaSupportDashboard extends Component {
    static template = "pba_customer_subscription.SupportDashboard";
    static components = { Layout };
    static props = { ...standardActionServiceProps };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.action = useService("action");
        this.fileInputRef = useRef("fileInput");
        this.state = useState({
            loading: true,
            error: "",
            context: {},
            tickets: [],
            finance: null,
            performance: null,
            activeTab: "tickets",
            showForm: false,
            editingId: null,
            formReadonly: false,
            currentTicket: null,
            form: this._emptyForm(),
            existingAttachments: [],
            pendingFiles: [],
            dragOver: false,
            messages: [],
            messageBody: "",
            ratingValue: "5",
            ratingText: "",
        });
        onWillStart(async () => {
            await this.loadAll();
        });
    }

    get display() {
        return {
            controlPanel: false,
        };
    }

    get ticketStats() {
        const tickets = this.state.tickets || [];
        return {
            total: tickets.length,
            pending: tickets.filter((ticket) => ticket.state === "pending_approval").length,
            open: tickets.filter((ticket) =>
                ["submitted", "in_progress"].includes(ticket.state)
            ).length,
            resolved: tickets.filter((ticket) => ticket.state === "resolved").length,
        };
    }

    _emptyForm() {
        return {
            name: "",
            description: "",
            priority: "1",
        };
    }

    roleLabel(role) {
        if (role === "admin") {
            return _t("Administrador");
        }
        if (role === "helpdesk") {
            return _t("Helpdesk");
        }
        if (role === "user") {
            return _t("Usuario");
        }
        return "";
    }

    stateLabel(state) {
        return STATE_LABELS[state] || state;
    }

    statusClass(state) {
        if (state === "pending_approval") {
            return "o_pba_status_pending";
        }
        if (state === "submitted") {
            return "o_pba_status_submitted";
        }
        if (state === "in_progress") {
            return "o_pba_status_progress";
        }
        if (state === "resolved") {
            return "o_pba_status_resolved";
        }
        return "o_pba_status_cancelled";
    }

    priorityLabel(priority) {
        return PRIORITY_LABELS[priority] || priority;
    }

    paymentStateLabel(state) {
        const labels = {
            not_paid: _t("No pagada"),
            partial: _t("Parcial"),
            in_payment: _t("En pago"),
            paid: _t("Pagada"),
            reversed: _t("Revertida"),
        };
        return labels[state] || state || "";
    }

    formatDate(value) {
        if (!value) {
            return "";
        }
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) {
            return value;
        }
        return date.toLocaleDateString();
    }

    formatDateTime(value) {
        if (!value) {
            return "";
        }
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) {
            return value;
        }
        return date.toLocaleString();
    }

    formatFileSize(size) {
        const value = Number(size) || 0;
        if (value < 1024) {
            return `${value} B`;
        }
        if (value < 1024 * 1024) {
            return `${(value / 1024).toFixed(1)} KB`;
        }
        return `${(value / (1024 * 1024)).toFixed(1)} MB`;
    }

    attachmentIcon(kind) {
        if (kind === "image") {
            return "fa-file-image-o";
        }
        if (kind === "video") {
            return "fa-file-video-o";
        }
        if (kind === "audio") {
            return "fa-file-audio-o";
        }
        return "fa-paperclip";
    }

    stripHtml(value) {
        const tmp = document.createElement("div");
        tmp.innerHTML = value || "";
        return tmp.textContent || tmp.innerText || "";
    }

    canComment() {
        const ticket = this.state.currentTicket;
        return Boolean(ticket && ticket.state !== "cancelled");
    }

    canRateCurrent() {
        return Boolean(this.state.currentTicket?.can_rate);
    }

    async loadAll() {
        this.state.loading = true;
        this.state.error = "";
        try {
            const context = await this.orm.call("pba.customer.support", "get_dashboard_context", []);
            this.state.context = context;
            if (!context.role || !context.configured) {
                this.state.tickets = [];
                this.state.finance = null;
                this.state.performance = null;
                return;
            }
            const [tickets, performance] = await Promise.all([
                this.orm.call("pba.customer.support", "get_tickets", []),
                this.orm.call("pba.customer.support", "get_performance_stats", []),
            ]);
            this.state.tickets = tickets;
            this.state.performance = performance;
            if (context.can_view_finance && this.state.activeTab === "finance") {
                this.state.finance = await this.orm.call(
                    "pba.customer.support",
                    "get_financial_summary",
                    []
                );
            }
        } catch (error) {
            this.state.error = error.data?.message || error.message || _t("Error inesperado");
        } finally {
            this.state.loading = false;
        }
    }

    async openTab(tab) {
        this.state.activeTab = tab;
        if (tab === "finance" && this.state.context.can_view_finance && !this.state.finance) {
            this.state.loading = true;
            try {
                this.state.finance = await this.orm.call(
                    "pba.customer.support",
                    "get_financial_summary",
                    []
                );
            } catch (error) {
                this.state.error = error.data?.message || error.message || _t("Error inesperado");
            } finally {
                this.state.loading = false;
            }
        }
    }

    openCreateForm() {
        if (!this.state.context.can_create) {
            this.notification.add(
                _t(
                    "Debe calificar el ticket %s antes de crear uno nuevo.",
                    this.state.context.unrated_ticket_number || ""
                ),
                { type: "warning" }
            );
            if (this.state.context.unrated_ticket_id) {
                const ticket = this.state.tickets.find(
                    (item) => item.id === this.state.context.unrated_ticket_id
                );
                if (ticket) {
                    this.openTicketForm(ticket);
                }
            }
            return;
        }
        this.state.editingId = null;
        this.state.formReadonly = false;
        this.state.currentTicket = null;
        this.state.form = this._emptyForm();
        this.state.existingAttachments = [];
        this.state.pendingFiles = [];
        this.state.dragOver = false;
        this.state.messages = [];
        this.state.messageBody = "";
        this.state.ratingValue = "5";
        this.state.ratingText = "";
        this.state.showForm = true;
        this.state.activeTab = "tickets";
    }

    async openTicketForm(ticket) {
        this.state.loading = true;
        try {
            const [detail, messages] = await Promise.all([
                this.orm.call("pba.customer.support", "get_ticket", [ticket.id]),
                this.orm.call("pba.customer.support", "get_messages", [ticket.id]),
            ]);
            this.state.editingId = detail.id;
            this.state.currentTicket = detail;
            this.state.formReadonly = !this.canEditTicket(detail);
            this.state.form = {
                name: detail.name || "",
                description: this.stripHtml(detail.description || ""),
                priority: detail.priority || "1",
            };
            this.state.existingAttachments = detail.attachments || [];
            this.state.pendingFiles = [];
            this.state.dragOver = false;
            this.state.messages = (messages || []).map((message) => ({
                ...message,
                body: markup(message.body || ""),
            }));
            this.state.messageBody = "";
            this.state.ratingValue = detail.rating || "5";
            this.state.ratingText = detail.rating_text || "";
            this.state.activeTab = "tickets";
            this.state.showForm = true;
        } catch (error) {
            this.notification.add(error.data?.message || error.message || _t("Error inesperado"), {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }

    closeForm() {
        this.state.showForm = false;
        this.state.editingId = null;
        this.state.formReadonly = false;
        this.state.currentTicket = null;
        this.state.form = this._emptyForm();
        this.state.existingAttachments = [];
        this.state.pendingFiles = [];
        this.state.messages = [];
        this.state.messageBody = "";
        this.state.ratingValue = "5";
        this.state.ratingText = "";
    }

    canEditTicket(ticket) {
        const ctx = this.state.context;
        if (!ctx.can_create_role) {
            return false;
        }
        if (!["pending_approval", "submitted"].includes(ticket.state)) {
            return false;
        }
        if (ctx.role === "user") {
            return ticket.client_user_login === ctx.user_login;
        }
        return true;
    }

    canApproveTicket(ticket) {
        return this.state.context.can_approve && ticket.state === "pending_approval";
    }

    canAttachFiles() {
        return !this.state.formReadonly && this.state.context.can_create_role;
    }

    openFilePicker() {
        this.fileInputRef.el?.click();
    }

    onDragOver() {
        if (this.canAttachFiles()) {
            this.state.dragOver = true;
        }
    }

    onDragLeave() {
        this.state.dragOver = false;
    }

    onDropFiles(ev) {
        this.state.dragOver = false;
        if (!this.canAttachFiles()) {
            return;
        }
        this._addFiles(Array.from(ev.dataTransfer?.files || []));
    }

    onSelectFiles(ev) {
        this._addFiles(Array.from(ev.target.files || []));
        if (this.fileInputRef.el) {
            this.fileInputRef.el.value = "";
        }
    }

    _addFiles(files) {
        for (const file of files) {
            if (file.size > MAX_ATTACHMENT_BYTES) {
                this.notification.add(
                    _t("El archivo %s supera el límite de 25 MB.", file.name),
                    { type: "danger" }
                );
                continue;
            }
            const exists = this.state.pendingFiles.some(
                (item) => item.name === file.name && item.size === file.size
            );
            if (!exists) {
                this.state.pendingFiles.push(file);
            }
        }
    }

    removePendingFile(index) {
        this.state.pendingFiles.splice(index, 1);
    }

    async _pendingFilesPayload() {
        const attachments = [];
        for (const file of this.state.pendingFiles) {
            attachments.push({
                name: file.name,
                mimetype: file.type || "application/octet-stream",
                datas: await fileToBase64(file),
            });
        }
        return attachments;
    }

    async saveTicket() {
        if (!this.state.form.name.trim()) {
            this.notification.add(_t("El asunto es obligatorio."), { type: "danger" });
            return;
        }
        this.state.loading = true;
        try {
            const values = {
                name: this.state.form.name.trim(),
                description: this.state.form.description || "",
                priority: this.state.form.priority || "1",
                attachments: await this._pendingFilesPayload(),
            };
            if (this.state.editingId) {
                await this.orm.call("pba.customer.support", "update_ticket", [
                    this.state.editingId,
                    values,
                ]);
                this.notification.add(_t("Ticket actualizado."), { type: "success" });
            } else {
                await this.orm.call("pba.customer.support", "create_ticket", [values]);
                this.notification.add(_t("Ticket creado."), { type: "success" });
            }
            this.closeForm();
            await this.loadAll();
        } catch (error) {
            this.notification.add(error.data?.message || error.message || _t("Error inesperado"), {
                type: "danger",
            });
            this.state.loading = false;
        }
    }

    async downloadAttachment(attachment) {
        this.state.loading = true;
        try {
            const data = await this.orm.call("pba.customer.support", "get_attachment", [
                this.state.editingId,
                attachment.id,
            ]);
            const byteCharacters = atob(data.datas || "");
            const byteNumbers = new Array(byteCharacters.length);
            for (let i = 0; i < byteCharacters.length; i++) {
                byteNumbers[i] = byteCharacters.charCodeAt(i);
            }
            const blob = new Blob([new Uint8Array(byteNumbers)], {
                type: data.mimetype || "application/octet-stream",
            });
            const url = URL.createObjectURL(blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = data.name || attachment.name || "attachment";
            document.body.appendChild(link);
            link.click();
            link.remove();
            URL.revokeObjectURL(url);
        } catch (error) {
            this.notification.add(error.data?.message || error.message || _t("Error inesperado"), {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }

    async removeExistingAttachment(attachment) {
        if (!this.canAttachFiles() || !this.state.editingId) {
            return;
        }
        this.state.loading = true;
        try {
            const ticket = await this.orm.call("pba.customer.support", "remove_attachment", [
                this.state.editingId,
                attachment.id,
            ]);
            this.state.existingAttachments = ticket.attachments || [];
            this.state.currentTicket = ticket;
            this.notification.add(_t("Adjunto eliminado."), { type: "success" });
            await this.loadAll();
        } catch (error) {
            this.notification.add(error.data?.message || error.message || _t("Error inesperado"), {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }

    async postMessage() {
        if (!this.state.editingId || !this.state.messageBody.trim()) {
            this.notification.add(_t("Escriba un mensaje."), { type: "warning" });
            return;
        }
        this.state.loading = true;
        try {
            const messages = await this.orm.call("pba.customer.support", "post_message", [
                this.state.editingId,
                { body: this.state.messageBody.trim() },
            ]);
            this.state.messages = (messages || []).map((message) => ({
                ...message,
                body: markup(message.body || ""),
            }));
            this.state.messageBody = "";
            this.notification.add(_t("Mensaje enviado."), { type: "success" });

        } catch (error) {
            this.notification.add(error.data?.message || error.message || _t("Error inesperado"), {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }

    async submitRating() {
        if (!this.state.editingId) {
            return;
        }
        this.state.loading = true;
        try {
            const ticket = await this.orm.call("pba.customer.support", "rate_ticket", [
                this.state.editingId,
                {
                    rating: this.state.ratingValue,
                    rating_text: this.state.ratingText,
                },
            ]);
            this.state.currentTicket = ticket;
            this.notification.add(_t("Gracias por su calificación."), { type: "success" });
            await this.loadAll();
        } catch (error) {
            this.notification.add(error.data?.message || error.message || _t("Error inesperado"), {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }

    async approveTicket(ticket) {
        this.state.loading = true;
        try {
            await this.orm.call("pba.customer.support", "approve_ticket", [ticket.id]);
            this.notification.add(_t("Ticket aprobado y enviado."), { type: "success" });
            await this.loadAll();
        } catch (error) {
            this.notification.add(error.data?.message || error.message || _t("Error inesperado"), {
                type: "danger",
            });
            this.state.loading = false;
        }
    }

    openSettings() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "res.config.settings",
            views: [[false, "form"]],
            target: "current",
            context: { module: "pba_customer_subscription" },
        });
    }

    formatAmount(amount, currency) {
        if (amount === undefined || amount === null) {
            return "";
        }
        const code = currency || "USD";
        try {
            return new Intl.NumberFormat(undefined, {
                style: "currency",
                currency: code,
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
            }).format(Number(amount));
        } catch (_error) {
            return `${Number(amount).toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
            })} ${code}`.trim();
        }
    }
}

registry.category("actions").add("pba_customer_subscription_dashboard", PbaSupportDashboard);
