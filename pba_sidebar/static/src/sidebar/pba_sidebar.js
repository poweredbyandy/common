/** @odoo-module **/

import { Component, useEffect, useRef, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useSortable } from "@web/core/utils/sortable_owl";

export class PbaSidebar extends Component {
    static template = "pba_sidebar.PbaSidebar";
    static props = {};

    setup() {
        this.ui = useState(useService("ui"));
        this.company = useService("company");
        this.sidebar = useService("pba_sidebar");
        this.state = useState(this.sidebar.state);
        this.local = useState({ showOpenHint: false });
        this.appsListRef = useRef("appsList");
        this.hideHintTimeout = null;

        useEffect(
            () => {
                document.body.classList.toggle(
                    "o_pba_sidebar_open",
                    this.state.isOpen && !this.ui.isSmall
                );
                if (this.state.isOpen) {
                    this.local.showOpenHint = false;
                }
            },
            () => [this.state.isOpen, this.ui.isSmall]
        );

        useSortable({
            enable: () => this.state.isReordering && !this.ui.isSmall,
            ref: this.appsListRef,
            elements: ".o_pba_sidebar_app",
            handle: ".o_pba_sidebar_app_handle",
            cursor: "grabbing",
            onDrop: ({ element, previous }) => this.onAppDrop({ element, previous }),
        });
    }

    get isVisible() {
        return !this.ui.isSmall;
    }

    get companyName() {
        return this.company.currentCompany?.name || "";
    }

    get companyLogoUrl() {
        const companyId = this.company.currentCompany?.id;
        if (!companyId) {
            return "/web/binary/company_logo";
        }
        return `/web/binary/company_logo?company=${companyId}`;
    }

    onHotzoneEnter() {
        if (this.hideHintTimeout) {
            clearTimeout(this.hideHintTimeout);
            this.hideHintTimeout = null;
        }
        this.local.showOpenHint = true;
    }

    onHotzoneLeave() {
        if (this.hideHintTimeout) {
            clearTimeout(this.hideHintTimeout);
        }
        this.hideHintTimeout = setTimeout(() => {
            this.local.showOpenHint = false;
            this.hideHintTimeout = null;
        }, 120);
    }

    openSidebar() {
        this.local.showOpenHint = false;
        this.sidebar.setOpen(true);
    }

    toggleSidebar() {
        this.sidebar.toggle();
    }

    toggleReorder() {
        this.sidebar.setReordering(!this.state.isReordering);
    }

    async onAppClick(app) {
        if (this.state.isReordering) {
            return;
        }
        await this.sidebar.openApp(app);
    }

    async onHistoryClick(entry) {
        await this.sidebar.openHistoryEntry(entry);
    }

    clearHistory() {
        this.sidebar.clearHistory();
    }

    async onAppDrop({ element, previous }) {
        const order = this.state.apps.map((app) => app.xmlid);
        const elementId = element.dataset.menuXmlid;
        const elementIndex = order.indexOf(elementId);
        if (elementIndex === -1) {
            return;
        }
        order.splice(elementIndex, 1);
        if (previous) {
            const prevIndex = order.indexOf(previous.dataset.menuXmlid);
            order.splice(prevIndex + 1, 0, elementId);
        } else {
            order.unshift(elementId);
        }
        await this.sidebar.saveAppOrder(order);
    }

    get historyEmptyLabel() {
        return _t("No hay páginas visitadas todavía");
    }
}

registry.category("main_components").add("PbaSidebar", {
    Component: PbaSidebar,
});
