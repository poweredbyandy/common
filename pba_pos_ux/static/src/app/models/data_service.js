/** @odoo-module **/

import { PosData } from "@point_of_sale/app/models/data_service";
import { filterIndexedDbPosData } from "@pba_pos_ux/utils/order_authority";
import { patch } from "@web/core/utils/patch";

patch(PosData.prototype, {
    initIndexedDB() {
        super.initIndexedDB(...arguments);
        const indexedDB = this.indexedDB;
        if (!indexedDB || indexedDB._pbaAuthorityPatched) {
            return;
        }
        const originalReadAll = indexedDB.readAll.bind(indexedDB);
        indexedDB.readAll = async (...args) =>
            filterIndexedDbPosData(await originalReadAll(...args));
        indexedDB._pbaAuthorityPatched = true;
    },
});
