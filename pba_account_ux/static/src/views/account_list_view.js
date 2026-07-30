/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { AccountGroupSearchPanel } from "@pba_account_ux/components/account_group_search_panel/account_group_search_panel";
import { AccountListRenderer } from "./account_list_renderer";

export const pbaAccountListView = {
    ...listView,
    SearchPanel: AccountGroupSearchPanel,
    Renderer: AccountListRenderer,
};

registry.category("views").add("pba_account_list", pbaAccountListView);
