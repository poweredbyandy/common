/** @odoo-module **/

import { PartnerList } from "@point_of_sale/app/screens/partner_list/partner_list";
import { patch } from "@web/core/utils/patch";

patch(PartnerList, {
    props: {
        ...PartnerList.props,
        forceCustomer: { type: Boolean, optional: true },
    },
});

patch(PartnerList.prototype, {
    clickPartner(partner) {
        if (this.props.forceCustomer && !partner) {
            return;
        }
        return super.clickPartner(...arguments);
    },
});
