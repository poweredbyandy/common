/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class AccountGroupSearchPanel extends Component {
    static template = "pba_account_ux.AccountGroupSearchPanel";
    static props = {};

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            items: [],
            selectedKey: "all",
            sidebarExpanded: true,
        });

        onWillStart(() => this.loadData());
    }

    async loadData() {
        const data = await this.orm.call("account.account", "get_group_panel_data", []);
        this.state.items = data.items || [];
    }

    clearPanelFilters() {
        const searchModel = this.env.searchModel;
        const toRemove = [];
        for (const [id, item] of Object.entries(searchModel.searchItems)) {
            if (item.pbaAccountGroupPanel) {
                toRemove.push(Number(id));
            }
        }
        if (!toRemove.length) {
            return;
        }
        searchModel.blockNotification = true;
        searchModel.query = searchModel.query.filter(
            (element) => !toRemove.includes(element.searchItemId)
        );
        for (const id of toRemove) {
            delete searchModel.searchItems[id];
        }
        searchModel.blockNotification = false;
    }

    clearGroupCategory() {
        const sections = this.env.searchModel.getSections(
            (section) => section.type === "category" && section.fieldName === "group_id"
        );
        const category = sections[0];
        if (category && category.activeValueId) {
            this.env.searchModel.blockNotification = true;
            category.activeValueId = false;
            this.env.searchModel.blockNotification = false;
        }
    }

    applySelection(selectedKey, domain, description) {
        this.state.selectedKey = selectedKey;
        this.clearPanelFilters();
        this.clearGroupCategory();
        if (domain) {
            this.env.searchModel.createNewFilters([
                {
                    description: description,
                    domain: domain,
                    pbaAccountGroupPanel: true,
                },
            ]);
        } else {
            this.env.searchModel._notify();
        }
    }

    selectAll() {
        this.applySelection("all", false, false);
    }

    selectGroup(item) {
        this.applySelection(
            `group-${item.id}`,
            `[["group_id","child_of",${item.id}]]`,
            item.label
        );
    }

    selectMissingGroup(item) {
        const ids = (item.account_ids || []).join(",");
        this.applySelection(
            `missing-${item.id}`,
            `[["id","in",[${ids}]]]`,
            item.label
        );
    }

    onItemClick(item) {
        if (item.type === "group") {
            this.selectGroup(item);
        } else {
            this.selectMissingGroup(item);
        }
    }

    async onCreateGroup(item, event) {
        event.stopPropagation();
        const accountId = item.sample_account_id || (item.account_ids || [])[0];
        if (!accountId) {
            return;
        }
        await this.action.doAction(
            {
                type: "ir.actions.act_window",
                name: _t("Create Account Group"),
                res_model: "account.account.create.group.wizard",
                views: [[false, "form"]],
                target: "new",
                context: {
                    default_account_id: accountId,
                    default_code_prefix_start: item.code,
                    default_code_prefix_end: item.code,
                    default_name: false,
                    active_id: accountId,
                },
            },
            {
                onClose: async () => {
                    await this.loadData();
                    this.selectAll();
                },
            }
        );
    }

    toggleSidebar() {
        this.state.sidebarExpanded = !this.state.sidebarExpanded;
    }

    isSelected(item) {
        if (item.type === "group") {
            return this.state.selectedKey === `group-${item.id}`;
        }
        return this.state.selectedKey === `missing-${item.id}`;
    }

    showCreateButton(item) {
        return item.type === "missing_group";
    }
}
