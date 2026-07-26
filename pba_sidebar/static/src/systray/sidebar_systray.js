/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class PbaSidebarSystray extends Component {
    static template = "pba_sidebar.Systray";
    static props = {};

    setup() {
        this.ui = useState(useService("ui"));
        this.sidebar = useService("pba_sidebar");
        this.state = useState(this.sidebar.state);
    }

    get isVisible() {
        return !this.ui.isSmall;
    }

    onClick() {
        this.sidebar.toggle();
    }
}

registry.category("systray").add(
    "pba_sidebar.systray",
    {
        Component: PbaSidebarSystray,
    },
    { sequence: 35 }
);
