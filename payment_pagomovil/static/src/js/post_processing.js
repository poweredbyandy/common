/** @odoo-module **/

import paymentPostProcessing from "@payment/js/post_processing";

paymentPostProcessing.include({
    /**
     * @override
     */
    _getFinalStates(providerCode) {
        const finalStates = this._super(...arguments);
        if (providerCode === "pagomovil") {
            finalStates.add("pending");
        }
        return finalStates;
    },
});
