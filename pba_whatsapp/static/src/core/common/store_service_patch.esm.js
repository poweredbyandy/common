import {Store} from "@mail/core/common/store_service";

import {patch} from "@web/core/utils/patch";

patch(Store.prototype, {
    tabToThreadType(tab) {
        const threadTypes = super.tabToThreadType(...arguments);
        if (tab === "gateway") {
            threadTypes.push("gateway");
        }
        return threadTypes;
    },
});
