import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { patch } from "@web/core/utils/patch";

patch(PartnerList.prototype, {
    getPartners() {
        return super
            .getPartners(...arguments)
            .filter((partner) => partner.type !== "delivery");
    },

    async getNewPartners() {
        const data = this.pos.data;
        const originalSearchRead = data.searchRead;
        data.searchRead = function (model, domain = [], fields = [], options = {}, queue = false) {
            if (model === "res.partner") {
                domain = [["type", "!=", "delivery"], ...domain];
            }
            return originalSearchRead.call(this, model, domain, fields, options, queue);
        };
        try {
            return await super.getNewPartners(...arguments);
        } finally {
            data.searchRead = originalSearchRead;
        }
    },
});
