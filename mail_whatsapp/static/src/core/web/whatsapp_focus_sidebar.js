/* @odoo-module */

import { Component, markup, onWillStart, useEffect, useState } from "@odoo/owl";
import { deserializeDateTime, formatDateTime } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { useService } from "@web/core/utils/hooks";
import { escape, escapeRegExp } from "@web/core/utils/strings";
import { useDebounced } from "@web/core/utils/timing";
import { htmlToTextContentInline } from "@mail/utils/common/format";
import { useVisible } from "@mail/utils/common/hooks";

const REPLIER_FILTER_ID = "replier-self";
const PAGE_SIZE = 30;

/** Session cache to avoid refetching tags / list on sidebar remounts. */
const focusCache = {
    tags: null,
    filterKey: null,
    channelIds: null,
    messageHits: null,
    previews: null,
    hasMore: false,
};

export class WhatsappFocusSidebar extends Component {
    static template = "mail_whatsapp.WhatsappFocusSidebar";
    static components = { Dropdown };
    static props = {};

    setup() {
        super.setup();
        this.store = useState(useService("mail.store"));
        this.orm = useService("orm");
        this.moreTagsDropdown = useDropdownState();
        this.state = useState({
            search: "",
            searching: false,
            loading: false,
            loadingMore: false,
            channelIds: [],
            messageHits: [],
            hasMore: false,
            /** @type {Object<number|string, {body: string, date: string|false, message_id: number, has_attachment: boolean}>} */
            previews: {},
            availableTags: [],
            /** @type {Object<string, boolean>} */
            selectedFilterIds: {},
        });
        this._fetchToken = 0;
        this._fetchedOffsets = new Set();
        this.debouncedSearch = useDebounced(this.runSearch.bind(this), 300);
        this.loadMoreState = useVisible(
            "load-more",
            (isVisible) => {
                if (isVisible && this.store.discuss.whatsappFocus) {
                    this.loadMore();
                }
            },
            { ready: false }
        );
        onWillStart(async () => {
            await this.loadFilterTags();
        });
        useEffect(
            (focus) => {
                if (focus) {
                    this.loadPage({ reset: true });
                } else {
                    this.loadMoreState.ready = false;
                }
            },
            () => [this.store.discuss.whatsappFocus]
        );
    }

    get filterKey() {
        return JSON.stringify({
            search: this.state.search.trim(),
            tags: this.selectedTagIds,
            replied: this.repliedByMe,
        });
    }

    get hasSearch() {
        return Boolean(this.state.search.trim());
    }

    get messagesSectionTitle() {
        return _t("Messages");
    }

    get selfReplierLabel() {
        const name = this.store.self?.name || _t("Me");
        return _t("Replied: %(name)s", { name });
    }

    get allFilterTags() {
        const tags = [
            {
                id: REPLIER_FILTER_ID,
                type: "replier",
                label: this.selfReplierLabel,
                color: false,
            },
        ];
        for (const tag of this.state.availableTags) {
            tags.push({
                id: `tag-${tag.id}`,
                type: "tag",
                tagId: tag.id,
                label: tag.name,
                color: tag.color ?? 0,
            });
        }
        return tags;
    }

    get visibleFilterTags() {
        return this.allFilterTags.filter((tag) => tag.id === REPLIER_FILTER_ID);
    }

    get overflowFilterTags() {
        return this.allFilterTags.filter((tag) => tag.id !== REPLIER_FILTER_ID);
    }

    get moreTagsCount() {
        return this.overflowFilterTags.length;
    }

    get hasOverflowFilterSelected() {
        return this.overflowFilterTags.some((tag) => this.isFilterSelected(tag.id));
    }

    get selectedFilterList() {
        return this.allFilterTags.filter((tag) => this.isFilterSelected(tag.id));
    }

    get selectedTagIds() {
        return this.selectedFilterList
            .filter((filter) => filter.type === "tag")
            .map((filter) => filter.tagId);
    }

    get repliedByMe() {
        return this.isFilterSelected(REPLIER_FILTER_ID);
    }

    invalidateListCache() {
        focusCache.filterKey = null;
        focusCache.channelIds = null;
        focusCache.messageHits = null;
        focusCache.previews = null;
        focusCache.hasMore = false;
        this._fetchedOffsets = new Set();
    }

    persistListCache() {
        focusCache.filterKey = this.filterKey;
        focusCache.channelIds = [...this.state.channelIds];
        focusCache.messageHits = [...this.state.messageHits];
        focusCache.previews = { ...this.state.previews };
        focusCache.hasMore = this.state.hasMore;
    }

    restoreListCache() {
        if (focusCache.filterKey !== this.filterKey || !focusCache.channelIds) {
            return false;
        }
        const missing = focusCache.channelIds.some(
            (id) => !this.store.Thread.get({ model: "discuss.channel", id })
        );
        if (missing) {
            return false;
        }
        this.state.channelIds = [...focusCache.channelIds];
        this.state.messageHits = [...(focusCache.messageHits || [])];
        this.state.previews = { ...(focusCache.previews || {}) };
        this.state.hasMore = Boolean(focusCache.hasMore);
        this._fetchedOffsets = new Set();
        for (let offset = 0; offset < this.state.channelIds.length; offset += PAGE_SIZE) {
            this._fetchedOffsets.add(offset);
        }
        return true;
    }

    applySearchResult(result, { append = false } = {}) {
        if (result?.data) {
            this.store.insert(result.data, { html: true });
        }
        if (result?.previews) {
            this.state.previews = { ...this.state.previews, ...result.previews };
        }
        const pageIds = result?.channel_ids || [];
        let added = 0;
        if (append) {
            const seen = new Set(this.state.channelIds);
            for (const id of pageIds) {
                if (!seen.has(id)) {
                    this.state.channelIds.push(id);
                    seen.add(id);
                    added += 1;
                }
            }
        } else {
            this.state.channelIds = pageIds;
            added = pageIds.length;
        }
        const hasMore = Boolean(result?.has_more);
        // Stop pagination if the server page did not advance the list.
        this.state.hasMore = hasMore && (added > 0 || !append);
        if (!append) {
            this.state.messageHits = result?.messages || [];
        }
        this.persistListCache();
    }

    getSearchKwargs(offset = 0) {
        return {
            limit: PAGE_SIZE,
            offset,
            tag_ids: this.selectedTagIds,
            replied_by_me: this.repliedByMe,
            include_messages: offset === 0,
        };
    }

    armLoadMore() {
        requestAnimationFrame(() => {
            if (!this.loadMoreState || this.state.loading || this.state.loadingMore) {
                return;
            }
            this.loadMoreState.ready = this.state.hasMore;
        });
    }

    async loadPage({ reset = false } = {}) {
        if (reset) {
            if (this.state.loading) {
                return;
            }
            if (this.restoreListCache()) {
                this.armLoadMore();
                return;
            }
            this.state.loading = true;
            this.state.hasMore = false;
            this.loadMoreState.ready = false;
            this._fetchedOffsets = new Set();
        } else {
            if (this.state.loadingMore || this.state.loading || !this.state.hasMore) {
                return;
            }
            this.state.loadingMore = true;
            this.loadMoreState.ready = false;
        }
        const offset = reset ? 0 : this.state.channelIds.length;
        if (this._fetchedOffsets.has(offset)) {
            this.state.loading = false;
            this.state.loadingMore = false;
            this.state.hasMore = false;
            this.persistListCache();
            return;
        }
        this._fetchedOffsets.add(offset);
        const term = this.state.search.trim();
        const token = ++this._fetchToken;
        try {
            const result = await this.orm.call(
                "discuss.channel",
                "whatsapp_focus_search",
                [term],
                this.getSearchKwargs(offset)
            );
            if (token !== this._fetchToken) {
                return;
            }
            this.applySearchResult(result, { append: !reset });
        } catch {
            if (token !== this._fetchToken) {
                return;
            }
            this._fetchedOffsets.delete(offset);
            if (reset) {
                this.state.channelIds = [];
                this.state.messageHits = [];
                this.state.hasMore = false;
                this.invalidateListCache();
            }
        } finally {
            if (token === this._fetchToken) {
                this.state.loading = false;
                this.state.loadingMore = false;
                this.armLoadMore();
            }
        }
    }

    async loadMore() {
        if (
            this.state.searching ||
            this.state.loading ||
            this.state.loadingMore ||
            !this.state.hasMore
        ) {
            return;
        }
        await this.loadPage({ reset: false });
    }

    async loadFilterTags() {
        if (focusCache.tags) {
            this.state.availableTags = focusCache.tags;
            return;
        }
        try {
            const tags = await this.orm.searchRead(
                "mail.whatsapp.tag",
                [],
                ["name", "color"],
                { order: "name" }
            );
            this.state.availableTags = tags;
            focusCache.tags = tags;
        } catch {
            this.state.availableTags = [];
        }
    }

    isFilterSelected(filterId) {
        return Boolean(this.state.selectedFilterIds[filterId]);
    }

    async toggleFilter(filterId) {
        if (this.state.selectedFilterIds[filterId]) {
            delete this.state.selectedFilterIds[filterId];
        } else {
            this.state.selectedFilterIds[filterId] = true;
        }
        this.invalidateListCache();
        await this.loadPage({ reset: true });
    }

    getPreviewData(thread) {
        return this.state.previews[thread.id] || this.state.previews[String(thread.id)];
    }

    getThreadSortDate(thread) {
        if (thread.newestMessage?.datetime) {
            return thread.newestMessage.datetime;
        }
        const preview = this.getPreviewData(thread);
        if (preview?.date) {
            const datetime = deserializeDateTime(preview.date);
            if (datetime?.isValid) {
                return datetime;
            }
        }
        return thread.lastInterestDateTime || thread.create_date;
    }

    get filteredThreads() {
        const threads = [];
        for (const id of this.state.channelIds) {
            const thread = this.getThreadById(id);
            if (thread) {
                threads.push(thread);
            }
        }
        return threads;
    }

    get messageHits() {
        return this.hasSearch ? this.state.messageHits : [];
    }

    get hasResults() {
        return (
            this.filteredThreads.length > 0 ||
            this.messageHits.length > 0 ||
            this.state.loading
        );
    }

    getPreview(thread) {
        const message = thread.newestMessage;
        if (message && !message.isEmpty) {
            return htmlToTextContentInline(message.body || "") || _t("Attachment");
        }
        const preview = this.getPreviewData(thread);
        if (!preview) {
            return "";
        }
        if (preview.body) {
            return preview.body;
        }
        if (preview.has_attachment) {
            return _t("Attachment");
        }
        return "";
    }

    getPreviewTime(thread) {
        if (thread.newestMessage?.dateSimple) {
            return thread.newestMessage.dateSimple;
        }
        if (thread.newestMessage?.datetimeShort) {
            return thread.newestMessage.datetimeShort;
        }
        const preview = this.getPreviewData(thread);
        if (!preview?.date) {
            return "";
        }
        const datetime = deserializeDateTime(preview.date);
        if (!datetime?.isValid) {
            return "";
        }
        if (datetime.hasSame(luxon.DateTime.now(), "day")) {
            return formatDateTime(datetime, {
                format: localization.shortTimeFormat || localization.timeFormat,
            });
        }
        return formatDateTime(datetime, { showSeconds: false });
    }

    getThreadById(channelId) {
        return this.store.Thread.get({ model: "discuss.channel", id: channelId });
    }

    getMessageAvatarUrl(hit) {
        return (
            this.getThreadById(hit.channel_id)?.avatarUrl ||
            "/web/static/img/user_menu_avatar.png"
        );
    }

    formatHitDate(hit) {
        if (!hit?.date) {
            return "";
        }
        const datetime = deserializeDateTime(hit.date);
        if (!datetime?.isValid) {
            return "";
        }
        return formatDateTime(datetime);
    }

    /**
     * Escape text and wrap case-insensitive search matches in <b>.
     * @param {string} text
     */
    highlightMatch(text) {
        const value = text || "";
        const term = this.state.search.trim();
        if (!value || !term) {
            return value;
        }
        const pattern = new RegExp(escapeRegExp(term), "gi");
        let html = "";
        let lastIndex = 0;
        for (const match of value.matchAll(pattern)) {
            html += escape(value.slice(lastIndex, match.index));
            html += `<b>${escape(match[0])}</b>`;
            lastIndex = match.index + match[0].length;
        }
        html += escape(value.slice(lastIndex));
        return markup(html);
    }

    onSearchInput(ev) {
        this.state.search = ev.target.value;
        const term = this.state.search.trim();
        this.invalidateListCache();
        if (!term) {
            this.state.messageHits = [];
            this.state.searching = false;
            this.loadPage({ reset: true });
            return;
        }
        this.debouncedSearch();
    }

    async runSearch() {
        const term = this.state.search.trim();
        this.invalidateListCache();
        if (!term) {
            this.state.messageHits = [];
            await this.loadPage({ reset: true });
            return;
        }
        this.state.searching = true;
        try {
            await this.loadPage({ reset: true });
        } finally {
            this.state.searching = false;
        }
    }

    async openThread(thread) {
        if (this.store.openWhatsAppChannel) {
            await this.store.openWhatsAppChannel(thread.id, thread.displayName);
            return;
        }
        thread.setAsDiscussThread();
    }

    async openMessage(hit) {
        if (this.store.openWhatsAppChannel) {
            await this.store.openWhatsAppChannel(hit.channel_id, hit.channel_name);
        }
        const thread = this.getThreadById(hit.channel_id);
        if (!thread) {
            return;
        }
        if (!this.store.discuss.thread?.eq(thread)) {
            thread.setAsDiscussThread();
        }
        const message =
            this.store.Message.get(hit.id) ||
            this.store.Message.insert({ id: hit.id, thread });
        thread.highlightMessage = message;
    }
}
