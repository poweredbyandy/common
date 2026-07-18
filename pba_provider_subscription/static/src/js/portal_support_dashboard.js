/** @odoo-module **/

import { Component, markup, onWillStart, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

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

const PRIORITY_HELP_FALLBACK = {
    "0": _t(
        "Consultas, mejoras o ajustes no urgentes que pueden atenderse con mayor holgura sin afectar la operación diaria."
    ),
    "1": _t(
        "Solicitudes o incidencias del día a día que afectan un proceso puntual, sin detener la operación general de la empresa."
    ),
    "2": _t(
        "Errores críticos para el funcionamiento de la empresa, pero la operación puede continuar. Requieren atención con un tiempo de espera acotado."
    ),
    "3": _t(
        "Errores de facturación o errores que impiden la operatividad del sistema. No deben superar el día."
    ),
};

const CATEGORY_LABELS = {
    consultation: _t("Consulta"),
    system_down: _t("Sistema Caído"),
    system_error: _t("Error de Sistema"),
    access: _t("Accesos y Permisos"),
    data: _t("Datos / Reportes"),
    improvement: _t("Mejora o Solicitud"),
    other: _t("Otro"),
};

const DESCRIPTION_QUESTIONS = {
    consultation: [
        "¿Qué necesita consultar o entender?",
        "¿En qué menú/módulo/pantalla ocurre?",
        "¿Qué ya intentó o revisó?",
        "¿Cuál es el resultado esperado?",
        "¿Hay fecha límite o impacto en operación?",
    ],
    system_down: [
        "¿Desde cuándo está caído el sistema o el servicio?",
        "¿Afecta a todos los usuarios o solo a algunos?",
        "¿Qué mensaje o pantalla ve exactamente?",
        "¿Qué acción estaba realizando cuando ocurrió?",
        "¿Hay impacto crítico en ventas, facturación u operación?",
    ],
    system_error: [
        "¿Qué error aparece (texto exacto o código)?",
        "¿Qué pasos exactos reproducen el problema?",
        "¿Ocurre siempre o solo a veces?",
        "¿Con qué usuario, empresa o documento falla?",
        "¿Qué resultado esperaba obtener?",
    ],
    access: [
        "¿Qué acceso o permiso necesita?",
        "¿Qué usuario o rol está involucrado?",
        "¿Qué menú/acción no puede usar actualmente?",
        "¿Es urgente para una operación en curso?",
        "¿Quién autoriza este acceso en su empresa?",
    ],
    data: [
        "¿Qué dato, reporte o documento está incorrecto?",
        "¿Cuál es el valor actual vs. el valor esperado?",
        "¿En qué fecha o documento se observa?",
        "¿Quién puede confirmar la información correcta?",
        "¿Necesita corrección, exportación o explicación?",
    ],
    improvement: [
        "¿Qué proceso quiere mejorar?",
        "¿Cuál es el dolor o fricción actual?",
        "¿Cómo lo resuelve hoy (workaround)?",
        "¿Cuál sería el comportamiento ideal?",
        "¿Qué beneficio aporta si se implementa?",
    ],
    other: [
        "¿Cuál es el problema o solicitud?",
        "¿Dónde ocurre (módulo, pantalla, proceso)?",
        "¿Qué pasos ya realizó?",
        "¿Cuál es el impacto para el negocio?",
        "¿Qué evidencia adjunta (foto/documento)?",
    ],
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

export class PbaPortalSupportDashboard extends Component {
    static template = "pba_provider_subscription.PortalSupportDashboard";
    static props = ["*"];

    setup() {
        this.fileInputRef = useRef("fileInput");
        this.supportModel = "pba.portal.support";
        this.state = useState({
            loading: true,
            error: "",
            context: {},
            tickets: [],
            finance: null,
            performance: null,
            activeTab: "tickets",
            ticketFilter: "open",
            ticketViewMode: "list",
            showForm: false,
            editingId: null,
            formReadonly: false,
            currentTicket: null,
            form: this._emptyForm(),
            descriptionAnswers: [],
            existingAttachments: [],
            pendingFiles: [],
            dragOver: false,
            messages: [],
            messageBody: "",
            ratingValue: "5",
            ratingText: "",
            flash: "",
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
            active: tickets.filter((ticket) =>
                ["pending_approval", "submitted", "in_progress"].includes(ticket.state)
            ).length,
            closed: tickets.filter((ticket) =>
                ["resolved", "cancelled"].includes(ticket.state)
            ).length,
            resolved: tickets.filter((ticket) => ticket.state === "resolved").length,
        };
    }

    get filteredTickets() {
        const tickets = this.state.tickets || [];
        const filter = this.state.ticketFilter;
        if (filter === "closed") {
            return tickets.filter((ticket) =>
                ["resolved", "cancelled"].includes(ticket.state)
            );
        }
        if (filter === "all") {
            return tickets;
        }
        return tickets.filter((ticket) =>
            ["pending_approval", "submitted", "in_progress"].includes(ticket.state)
        );
    }

    get kanbanColumns() {
        const openStates = ["pending_approval", "submitted", "in_progress"];
        const closedStates = ["resolved", "cancelled"];
        let states = openStates;
        if (this.state.ticketFilter === "closed") {
            states = closedStates;
        } else if (this.state.ticketFilter === "all") {
            states = [...openStates, ...closedStates];
        }
        const tickets = this.filteredTickets;
        return states.map((state) => ({
            state,
            label: this.stateLabel(state),
            tickets: tickets.filter((ticket) => ticket.state === state),
        }));
    }

    setTicketFilter(filter) {
        this.state.ticketFilter = filter;
    }

    setTicketViewMode(mode) {
        this.state.ticketViewMode = mode;
    }

    _emptyForm() {
        return {
            name: "",
            category: "consultation",
            description: "",
            priority: "1",
        };
    }

    _buildDescriptionAnswers(category, keepAnswers = false) {
        const questions = DESCRIPTION_QUESTIONS[category] || DESCRIPTION_QUESTIONS.other;
        const previous = keepAnswers ? this.state.descriptionAnswers || [] : [];
        return questions.map((question, index) => ({
            question,
            answer: previous[index]?.answer || "",
        }));
    }

    _escapeHtml(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");
    }

    _composeDescriptionFromAnswers(answers) {
        return (answers || [])
            .map((item, index) => {
                const question = this._escapeHtml(item.question);
                const answer = this._escapeHtml((item.answer || "").trim()).replace(
                    /\n/g,
                    "<br/>"
                );
                return (
                    `<p><strong>${index + 1}. ${question}</strong></p>` +
                    `<p>${answer}</p>` +
                    `<p><br/></p>`
                );
            })
            .join("");
    }

    categoryLabel(category) {
        return CATEGORY_LABELS[category] || category || "";
    }

    get categoryOptions() {
        return Object.entries(CATEGORY_LABELS).map(([value, label]) => ({
            value,
            label,
        }));
    }

    onCategoryChange(ev) {
        if (this.state.formReadonly || this.state.editingId) {
            this.state.form.category = ev.target.value;
            return;
        }
        const nextCategory = ev.target.value;
        this.state.form.category = nextCategory;
        this.state.descriptionAnswers = this._buildDescriptionAnswers(nextCategory, false);
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

    get priorityOptions() {
        const config = this.state.context?.sla_config?.priorities || [];
        if (config.length) {
            return config.map((item) => ({
                value: item.key,
                label: PRIORITY_LABELS[item.key] || item.label,
                durationLabel: item.duration_label || "",
                help: item.help || PRIORITY_HELP_FALLBACK[item.key] || "",
            }));
        }
        return Object.keys(PRIORITY_LABELS).map((key) => ({
            value: key,
            label: PRIORITY_LABELS[key],
            durationLabel: "",
            help: PRIORITY_HELP_FALLBACK[key] || "",
        }));
    }

    isImprovementCategory(category = null) {
        return (category || this.state.form?.category) === "improvement";
    }

    ticketHasSla(ticket) {
        return Boolean(ticket) && ticket.category !== "improvement";
    }

    selectedPriorityEstimate() {
        if (this.isImprovementCategory()) {
            return "";
        }
        const priority = this.state.form?.priority || "1";
        const option = this.priorityOptions.find((item) => item.value === priority);
        return option?.durationLabel || "";
    }

    businessHoursLabel() {
        if (this.isImprovementCategory()) {
            return "";
        }
        return this.state.context?.sla_config?.business_hours?.label || "";
    }

    selectedPriorityHelp() {
        const priority = this.state.form?.priority || "1";
        const option = this.priorityOptions.find((item) => item.value === priority);
        return option?.help || PRIORITY_HELP_FALLBACK[priority] || "";
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
        const html = String(value || "")
            .replace(/<\s*br\s*\/?>/gi, "\n")
            .replace(/<\/\s*p\s*>/gi, "\n")
            .replace(/<\/\s*div\s*>/gi, "\n")
            .replace(/<\s*p[^>]*>/gi, "")
            .replace(/<\s*div[^>]*>/gi, "");
        const tmp = document.createElement("div");
        tmp.innerHTML = html;
        return (tmp.textContent || tmp.innerText || "").replace(/\n{3,}/g, "\n\n").trim();
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
            const context = await this._callSupport("get_dashboard_context", []);
            this.state.context = context;
            if (!context.role || !context.configured) {
                this.state.tickets = [];
                this.state.finance = null;
                this.state.performance = null;
                return;
            }
            const [tickets, performance] = await Promise.all([
                this._callSupport("get_tickets", []),
                this._callSupport("get_performance_stats", []),
            ]);
            this.state.tickets = tickets;
            this.state.performance = performance;
            if (context.can_view_finance && this.state.activeTab === "finance") {
                this.state.finance = await this._callSupport("get_financial_summary", []);
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
                this.state.finance = await this._callSupport("get_financial_summary", []);
            } catch (error) {
                this.state.error = error.data?.message || error.message || _t("Error inesperado");
            } finally {
                this.state.loading = false;
            }
        }
    }

    openCreateForm() {
        if (!this.state.context.can_create) {
            this._notify(
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
        this.state.descriptionAnswers = this._buildDescriptionAnswers(
            this.state.form.category
        );
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
                this._callSupport("get_ticket", [ticket.id]),
                this._callSupport("get_messages", [ticket.id]),
            ]);
            this.state.editingId = detail.id;
            this.state.currentTicket = detail;
            this.state.formReadonly = !this.canEditTicket(detail);
            this.state.form = {
                name: detail.name || "",
                category: detail.category || "consultation",
                description: this.stripHtml(detail.description || ""),
                priority: detail.priority || "1",
            };
            this.state.descriptionAnswers = [];
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
            this._notify(error.data?.message || error.message || _t("Error inesperado"), {
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
        this.state.descriptionAnswers = [];
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
        if (!this.state.context.can_create_role) {
            return false;
        }
        if (!this.state.editingId) {
            return true;
        }
        const ticket = this.state.currentTicket;
        if (!ticket || ["resolved", "cancelled"].includes(ticket.state)) {
            return false;
        }
        if (ticket.can_attach === false) {
            return false;
        }
        if (this.state.context.role === "user") {
            return ticket.client_user_login === this.state.context.user_login;
        }
        return true;
    }

    canRemoveAttachments() {
        if (!this.canAttachFiles()) {
            return false;
        }
        const ticket = this.state.currentTicket;
        if (!ticket) {
            return !this.state.formReadonly;
        }
        if (ticket.can_remove_attachment === false) {
            return false;
        }
        return ["pending_approval", "submitted"].includes(ticket.state);
    }

    _shouldUploadAttachmentsImmediately() {
        return Boolean(this.state.editingId && this.state.formReadonly && this.canAttachFiles());
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

    async onDropFiles(ev) {
        this.state.dragOver = false;
        if (!this.canAttachFiles()) {
            return;
        }
        await this._addFiles(Array.from(ev.dataTransfer?.files || []));
    }

    async onSelectFiles(ev) {
        await this._addFiles(Array.from(ev.target.files || []));
        if (this.fileInputRef.el) {
            this.fileInputRef.el.value = "";
        }
    }

    async _addFiles(files) {
        for (const file of files) {
            if (file.size > MAX_ATTACHMENT_BYTES) {
                this._notify(
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
        if (this.state.pendingFiles.length && this._shouldUploadAttachmentsImmediately()) {
            await this.uploadPendingAttachments();
        }
    }

    async uploadPendingAttachments() {
        if (!this.state.editingId || !this.state.pendingFiles.length) {
            return;
        }
        this.state.loading = true;
        try {
            const ticket = await this._callSupport("add_attachments", [
                this.state.editingId,
                await this._pendingFilesPayload(),
            ]);
            this.state.pendingFiles = [];
            this.state.existingAttachments = ticket.attachments || [];
            this.state.currentTicket = ticket;
            this._notify(_t("Adjuntos enviados."), { type: "success" });
            await this.loadAll();
            if (this.state.editingId) {
                const detail = this.state.tickets.find((item) => item.id === this.state.editingId);
                if (detail) {
                    this.state.currentTicket = {
                        ...this.state.currentTicket,
                        ...detail,
                    };
                    this.state.existingAttachments =
                        this.state.currentTicket.attachments || this.state.existingAttachments;
                }
            }
        } catch (error) {
            this._notify(error.data?.message || error.message || _t("Error inesperado"), {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
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
            this._notify(_t("El asunto es obligatorio."), { type: "danger" });
            return;
        }
        if (!this.state.form.category) {
            this._notify(_t("La categoría es obligatoria."), { type: "danger" });
            return;
        }
        let description = (this.state.form.description || "").trim();
        if (!this.state.editingId) {
            const unanswered = (this.state.descriptionAnswers || []).find(
                (item) => !(item.answer || "").trim()
            );
            if (unanswered) {
                this._notify(
                    _t("Debe responder todas las preguntas de la descripción."),
                    { type: "danger" }
                );
                return;
            }
            description = this._composeDescriptionFromAnswers(
                this.state.descriptionAnswers
            ).trim();
        }
        if (!description) {
            this._notify(
                _t("Complete la descripción respondiendo las preguntas sugeridas."),
                { type: "danger" }
            );
            return;
        }
        if (!this.state.editingId && !this.state.pendingFiles.length) {
            this._notify(
                _t("Debe adjuntar al menos una foto o documento como evidencia."),
                { type: "danger" }
            );
            return;
        }
        this.state.loading = true;
        try {
            const values = {
                name: this.state.form.name.trim(),
                category: this.state.form.category,
                description,
                priority: this.state.form.priority || "1",
                attachments: await this._pendingFilesPayload(),
            };
            if (this.state.editingId) {
                await this._callSupport("update_ticket", [
                    this.state.editingId,
                    values,
                ]);
                this._notify(_t("Ticket actualizado."), { type: "success" });
            } else {
                await this._callSupport("create_ticket", [values]);
                this._notify(_t("Ticket creado."), { type: "success" });
            }
            this.closeForm();
            await this.loadAll();
        } catch (error) {
            this._notify(error.data?.message || error.message || _t("Error inesperado"), {
                type: "danger",
            });
            this.state.loading = false;
        }
    }

    async downloadAttachment(attachment) {
        this.state.loading = true;
        try {
            const data = await this._callSupport("get_attachment", [
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
            this._notify(error.data?.message || error.message || _t("Error inesperado"), {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }

    async removeExistingAttachment(attachment) {
        if (!this.canRemoveAttachments() || !this.state.editingId) {
            return;
        }
        this.state.loading = true;
        try {
            const ticket = await this._callSupport("remove_attachment", [
                this.state.editingId,
                attachment.id,
            ]);
            this.state.existingAttachments = ticket.attachments || [];
            this.state.currentTicket = ticket;
            this._notify(_t("Adjunto eliminado."), { type: "success" });
            await this.loadAll();
        } catch (error) {
            this._notify(error.data?.message || error.message || _t("Error inesperado"), {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }

    async postMessage() {
        if (!this.state.editingId || !this.state.messageBody.trim()) {
            this._notify(_t("Escriba un mensaje."), { type: "warning" });
            return;
        }
        this.state.loading = true;
        try {
            const messages = await this._callSupport("post_message", [
                this.state.editingId,
                { body: this.state.messageBody.trim() },
            ]);
            this.state.messages = (messages || []).map((message) => ({
                ...message,
                body: markup(message.body || ""),
            }));
            this.state.messageBody = "";
            this._notify(_t("Mensaje enviado."), { type: "success" });

        } catch (error) {
            this._notify(error.data?.message || error.message || _t("Error inesperado"), {
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
        const ratingText = (this.state.ratingText || "").trim();
        if (ratingText.length < 20) {
            this._notify(
                _t("El comentario de la calificación debe tener al menos 20 caracteres."),
                { type: "danger" }
            );
            return;
        }
        this.state.loading = true;
        try {
            const ticket = await this._callSupport("rate_ticket", [
                this.state.editingId,
                {
                    rating: this.state.ratingValue,
                    rating_text: ratingText,
                },
            ]);
            this.state.currentTicket = ticket;
            this._notify(_t("Gracias por su calificación."), { type: "success" });
            await this.loadAll();
        } catch (error) {
            this._notify(error.data?.message || error.message || _t("Error inesperado"), {
                type: "danger",
            });
        } finally {
            this.state.loading = false;
        }
    }

    async approveTicket(ticket) {
        this.state.loading = true;
        try {
            await this._callSupport("approve_ticket", [ticket.id]);
            this._notify(_t("Ticket aprobado y enviado."), { type: "success" });
            await this.loadAll();
        } catch (error) {
            this._notify(error.data?.message || error.message || _t("Error inesperado"), {
                type: "danger",
            });
            this.state.loading = false;
        }
    }

    openSettings() {
        return;
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
    async _callSupport(method, args = []) {
        return rpc("/my/support/call", {
            method,
            args,
        });
    }

    _notify(message, options = {}) {
        this.state.flash = message;
        const type = options.type || "info";
        if (type === "danger") {
            this.state.error = message;
        }
        setTimeout(() => {
            if (this.state.flash === message) {
                this.state.flash = "";
            }
        }, 3500);
    }

}

registry.category("public_components").add("pba_provider_subscription.PortalSupportDashboard", PbaPortalSupportDashboard);
