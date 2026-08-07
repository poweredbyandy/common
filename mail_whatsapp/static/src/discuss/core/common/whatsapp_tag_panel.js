/* @odoo-module */

import { ActionPanel } from "@mail/discuss/core/common/action_panel";

import { Component, onMounted, useRef, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class WhatsappTagPanel extends Component {
    static components = { ActionPanel };
    static defaultProps = { hasSizeConstraints: false };
    static props = ["hasSizeConstraints?", "thread", "close", "className?"];
    static template = "mail_whatsapp.WhatsappTagPanel";

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.inputRef = useRef("input");
        this.state = useState({
            availableTags: [],
            query: "",
            saving: false,
        });
        onMounted(async () => {
            await this.loadAvailableTags();
            this.inputRef.el?.focus();
        });
    }

    get selectedTagIds() {
        return new Set((this.props.thread.whatsappTags || []).map((tag) => tag.id));
    }

    get filteredTags() {
        const query = this.state.query.trim().toLowerCase();
        if (!query) {
            return this.state.availableTags;
        }
        return this.state.availableTags.filter((tag) =>
            tag.name.toLowerCase().includes(query)
        );
    }

    get canCreate() {
        const query = this.state.query.trim();
        if (!query) {
            return false;
        }
        return !this.state.availableTags.some(
            (tag) => tag.name.toLowerCase() === query.toLowerCase()
        );
    }

    async loadAvailableTags() {
        const tags = await this.orm.searchRead(
            "mail.whatsapp.tag",
            [],
            ["name", "color"],
            { order: "name" }
        );
        this.state.availableTags = tags;
    }

    async persistTagIds(tagIds) {
        this.state.saving = true;
        try {
            const tags = await this.orm.call(
                "discuss.channel",
                "set_whatsapp_tag_ids",
                [[this.props.thread.id], tagIds]
            );
            this.props.thread.whatsappTags = tags;
        } catch (error) {
            this.notification.add(
                error?.data?.message || _t("Could not update tags."),
                { type: "danger" }
            );
        } finally {
            this.state.saving = false;
        }
    }

    async onToggleTag(tag) {
        const selected = new Set(this.selectedTagIds);
        if (selected.has(tag.id)) {
            selected.delete(tag.id);
        } else {
            selected.add(tag.id);
        }
        await this.persistTagIds([...selected]);
    }

    async onCreateTag() {
        const name = this.state.query.trim();
        if (!name || !this.canCreate) {
            return;
        }
        this.state.saving = true;
        try {
            const created = await this.orm.create("mail.whatsapp.tag", [
                { name, color: Math.floor(Math.random() * 11) },
            ]);
            const tagId = Array.isArray(created) ? created[0] : created;
            await this.loadAvailableTags();
            const selected = [...this.selectedTagIds, tagId];
            await this.persistTagIds(selected);
            this.state.query = "";
        } catch (error) {
            this.notification.add(
                error?.data?.message || _t("Could not create the tag."),
                { type: "danger" }
            );
        } finally {
            this.state.saving = false;
        }
    }

    onInput(ev) {
        this.state.query = ev.target.value;
    }

    onKeydown(ev) {
        if (ev.key === "Enter" && this.canCreate) {
            ev.preventDefault();
            this.onCreateTag();
        }
    }
}
