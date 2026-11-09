/* @odoo-module */

import { Record } from "@mail/core/common/record";
import { Thread } from "@mail/core/common/thread_model";
import { imageUrl } from "@web/core/utils/urls";
import { patch } from "@web/core/utils/patch";

patch(Thread.prototype, {
    setup() {
        super.setup(...arguments);
        this.whatsapp_partner_id = Record.one("Persona");
        /** @type {string|false} */
        this.whatsappNumber = false;
        /** @type {number|false} */
        this.whatsappCompanyId = false;
        /** @type {string|false} */
        this.whatsappCompanyName = false;
        /** @type {number|false} */
        this.whatsappResponsibleId = false;
        /** @type {string|false} */
        this.whatsappResponsibleName = false;
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
    get whatsappResponsibleAvatarUrl() {
        if (!this.whatsappResponsibleId) {
            return "";
        }
        return imageUrl("res.users", this.whatsappResponsibleId, "avatar_128");
    },
    get whatsappSidebarTags() {
        if (this.channel_type !== "whatsapp") {
            return [];
        }
        const tags = [];
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

