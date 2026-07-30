/** @odoo-module **/

import { ListRenderer } from "@web/views/list/list_renderer";
import { onMounted, onPatched, onWillUnmount, useEffect } from "@odoo/owl";

export class AccountListRenderer extends ListRenderer {
    setup() {
        super.setup();
        this._pbaLastScrollKey = null;
        this._pbaPendingFocus = null;
        this._pbaOnCodeInput = this._pbaOnCodeInput.bind(this);

        onMounted(() => {
            this.rootRef.el?.addEventListener("input", this._pbaOnCodeInput);
        });
        onWillUnmount(() => {
            this.rootRef.el?.removeEventListener("input", this._pbaOnCodeInput);
            this._pbaClearCreatingLayout();
        });

        useEffect(
            () => {
                const record = this.props.list.editedRecord;
                if (record?.isNew) {
                    const code = this._pbaGetTypedCode(record);
                    this._pbaSyncCreatePosition(code);
                    this._pbaScrollListToCode(code);
                } else {
                    this._pbaLastScrollKey = null;
                    this._pbaPendingFocus = null;
                    this._pbaClearCreatingLayout();
                }
            },
            () => [this.props.list.editedRecord?.id, this.props.list.editedRecord?.isNew]
        );

        onPatched(() => {
            if (this._pbaPendingFocus) {
                const pending = this._pbaPendingFocus;
                this._pbaPendingFocus = null;
                this._pbaRestoreCodeFocus(pending);
            }
            if (this.props.list.editedRecord?.isNew) {
                this._pbaEnsureCreatingLayout(this._pbaGetTypedCode(this.props.list.editedRecord));
            } else {
                this._pbaClearCreatingLayout();
            }
        });
    }

    getRowClass(record) {
        const classNames = super.getRowClass(record);
        if (record.isNew && record.isInEdition) {
            return `${classNames} o_pba_creating_account_row`;
        }
        return classNames;
    }

    _pbaGetTypedCode(record) {
        const row = this._pbaGetCreateRow();
        const input = row?.querySelector("td.o_data_cell[name='code'] input");
        if (input && document.activeElement === input) {
            return input.value || "";
        }
        return (record?.data?.code || "").toString();
    }

    _pbaOnCodeInput(ev) {
        const input = ev.target;
        if (!input || input.tagName !== "INPUT") {
            return;
        }
        const cell = input.closest("td.o_data_cell[name='code']");
        if (!cell) {
            return;
        }
        const row = cell.closest("tr.o_data_row");
        const record = this.props.list.editedRecord;
        if (!record?.isNew || !row || row.dataset.id !== String(record.id)) {
            return;
        }
        const value = input.value || "";
        const selectionStart = input.selectionStart;
        const selectionEnd = input.selectionEnd;
        if ((record.data.code || "") !== value) {
            record.dirty = true;
            record._applyChanges({ code: value });
        }
        const moved = this._pbaSyncCreatePosition(value, {
            value,
            selectionStart,
            selectionEnd,
        });
        this._pbaScrollListToCode(value);
        if (moved) {
            this._pbaRestoreCodeFocus({
                value,
                selectionStart,
                selectionEnd,
            });
        }
    }

    _pbaRestoreCodeFocus({ value, selectionStart, selectionEnd }) {
        const restore = () => {
            const record = this.props.list.editedRecord;
            if (!record?.isNew) {
                return;
            }
            const input = this._pbaGetCreateRow()?.querySelector(
                "td.o_data_cell[name='code'] input"
            );
            if (!input) {
                return;
            }
            if (value != null && input.value !== value) {
                input.value = value;
            }
            input.focus({ preventScroll: true });
            const length = input.value.length;
            const start = Math.min(selectionStart ?? length, length);
            const end = Math.min(selectionEnd ?? length, length);
            try {
                input.setSelectionRange(start, end);
            } catch {
                // ignore invalid selection on some inputs
            }
            const codeColumn = this.columns.find((column) => column.name === "code");
            if (codeColumn) {
                this.cellToFocus = { record, column: codeColumn };
                this.lastEditedCell = { column: codeColumn, record };
                this.activeRowId = record.id;
            }
        };
        requestAnimationFrame(() => {
            requestAnimationFrame(restore);
        });
    }

    _pbaGetRecordSortCode(record) {
        return (record.data.code || record.data.placeholder_code || "").toString();
    }

    _pbaCompareCodes(left, right) {
        return left.localeCompare(right);
    }

    _pbaGetCreateRow() {
        const record = this.props.list.editedRecord;
        if (!record?.isNew) {
            return null;
        }
        return this.tableRef.el?.querySelector(
            `tbody tr.o_data_row[data-id="${record.id}"]`
        );
    }

    _pbaClearCreatingLayout() {
        this.rootRef.el?.classList.remove("o_pba_has_creating_account");
        this.rootRef.el?.style.removeProperty("--pba-creating-sticky-top");
    }

    _pbaFindPredecessor(prefix, others) {
        if (!prefix) {
            return null;
        }
        let predecessor = null;
        for (const other of others) {
            const otherCode = this._pbaGetRecordSortCode(other);
            if (!otherCode) {
                continue;
            }
            if (otherCode.startsWith(prefix)) {
                predecessor = other;
                continue;
            }
            if (this._pbaCompareCodes(otherCode, prefix) < 0) {
                predecessor = other;
                continue;
            }
            break;
        }
        return predecessor;
    }

    _pbaGetInsertIndex(code, recordsWithoutCreate) {
        const normalizedCode = (code || "").toString();
        if (!normalizedCode) {
            return 0;
        }
        const predecessor = this._pbaFindPredecessor(normalizedCode, recordsWithoutCreate);
        if (predecessor) {
            return recordsWithoutCreate.indexOf(predecessor) + 1;
        }
        for (let i = 0; i < recordsWithoutCreate.length; i++) {
            if (
                this._pbaCompareCodes(
                    this._pbaGetRecordSortCode(recordsWithoutCreate[i]),
                    normalizedCode
                ) > 0
            ) {
                return i;
            }
        }
        return recordsWithoutCreate.length;
    }

    _pbaSyncCreatePosition(code, focusState = null) {
        const list = this.props.list;
        const record = list.editedRecord;
        if (!record?.isNew || list.isGrouped) {
            return false;
        }
        const currentIndex = list.records.indexOf(record);
        if (currentIndex < 0) {
            return false;
        }
        const others = list.records.filter((item) => item !== record);
        const insertAt = this._pbaGetInsertIndex(code, others);
        if (insertAt === currentIndex) {
            return false;
        }
        list.records.splice(currentIndex, 1);
        list.records.splice(insertAt, 0, record);
        if (focusState) {
            this._pbaPendingFocus = focusState;
        }
        return true;
    }

    _pbaEnsureCreatingLayout(code = "") {
        const scrollEl = this.rootRef.el;
        const table = this.tableRef.el;
        const createRow = this._pbaGetCreateRow();
        if (!scrollEl || !table || !createRow) {
            return 0;
        }
        const thead = table.querySelector("thead");
        const rowHeight = createRow.getBoundingClientRect().height || 35;
        const theadHeight = thead?.getBoundingClientRect().height || 0;
        const normalizedCode = (code || "").toString();
        const stickyTop = normalizedCode ? theadHeight + 3 * rowHeight : theadHeight;
        scrollEl.style.setProperty("--pba-creating-sticky-top", `${stickyTop}px`);
        scrollEl.classList.add("o_pba_has_creating_account");
        return stickyTop;
    }

    _pbaScrollListToCode(code) {
        const list = this.props.list;
        const record = list.editedRecord;
        const scrollEl = this.rootRef.el;
        const table = this.tableRef.el;
        if (!record?.isNew || list.isGrouped || !scrollEl || !table) {
            return;
        }

        const normalizedCode = (code || "").toString();
        const stickyTop = this._pbaEnsureCreatingLayout(normalizedCode);
        const createRow = this._pbaGetCreateRow();
        if (!createRow) {
            return;
        }

        const others = list.records.filter((item) => item !== record);
        const predecessor = this._pbaFindPredecessor(normalizedCode, others);
        const scrollKey = `${normalizedCode}:${predecessor ? predecessor.id : "empty-top"}`;
        if (scrollKey === this._pbaLastScrollKey) {
            return;
        }
        this._pbaLastScrollKey = scrollKey;

        requestAnimationFrame(() => {
            if (!normalizedCode) {
                scrollEl.scrollTop = 0;
                return;
            }
            const scrollRect = scrollEl.getBoundingClientRect();
            const desiredCreateTop = scrollRect.top + stickyTop;
            if (predecessor) {
                const targetRow = table.querySelector(
                    `tbody tr.o_data_row[data-id="${predecessor.id}"]`
                );
                if (targetRow) {
                    const targetRect = targetRow.getBoundingClientRect();
                    scrollEl.scrollTop += targetRect.bottom - desiredCreateTop;
                    return;
                }
            }
            const createRect = createRow.getBoundingClientRect();
            scrollEl.scrollTop += createRect.top - desiredCreateTop;
        });
    }
}
