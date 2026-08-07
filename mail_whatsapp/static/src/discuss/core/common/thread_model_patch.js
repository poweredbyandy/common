/* @odoo-module */

import { Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup(...arguments);
        this.whatsapp_partner_id = Record.one("Persona");
        /** @type {string|false} */
        this.whatsappLastReplierName = false;
        /** @type {number|false} */
        this.whatsappLastReplierPartnerId = false;
        /** @type {string|false} */
        this.whatsappNumber = false;
        /** @type {{id: number, name: string, color: number}[]} */
        this.whatsappTags = [];
        this.whatsappMember = Record.one("ChannelMember", {
            compute() {
                return (
                    this.channel_type === "whatsapp" &&
                    this.channelMembers.find((member) =>
                        member.persona?.eq(this.whatsapp_partner_id)
                    )
                );
            },
        });
    },
    _computeOfflineMembers() {
        const res = super._computeOfflineMembers();
        if (this.channel_type === "whatsapp") {
            return res.filter((member) => member.persona?.notEq(this.whatsapp_partner_id));
        }
        return res;
    },
    computeCorrespondent() {
        if (this.channel_type === "whatsapp" && this.whatsapp_partner_id) {
            const member = this.channelMembers.find((m) =>
                m.persona?.eq(this.whatsapp_partner_id)
            );
            if (member) {
                return member;
            }
        }
        return super.computeCorrespondent();
    },
    get hasMemberList() {
        return this.channel_type === "whatsapp" || super.hasMemberList;
    },
    get whatsappSidebarTags() {
        if (this.channel_type !== "whatsapp") {
            return [];
        }
        const tags = [];
        if (this.whatsappLastReplierName) {
            tags.push({
                id: "replier",
                label: _t("Replied: %(name)s", {
                    name: this.whatsappLastReplierName,
                }),
                title: _t("%(name)s replied to this conversation", {
                    name: this.whatsappLastReplierName,
                }),
                color: false,
            });
        }
        for (const tag of this.whatsappTags || []) {
            tags.push({
                id: `tag-${tag.id}`,
                label: tag.name,
                title: tag.name,
                color: tag.color ?? 0,
            });
        }
        return tags;
    },
});

