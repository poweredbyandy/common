/** @odoo-module **/

import DevicesSynchronisation from "@point_of_sale/app/store/devices_synchronisation";
import { patch } from "@web/core/utils/patch";

patch(DevicesSynchronisation.prototype, {
    processDynamicRecords(dynamicRecords) {
        const result = super.processDynamicRecords(...arguments);
        this.pos.pbaReclaimActiveSharedOrderSession?.();
        return result;
    },
});
