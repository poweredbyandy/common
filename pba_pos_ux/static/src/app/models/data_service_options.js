/** @odoo-module **/

import { DataServiceOptions } from "@point_of_sale/app/models/data_service_options";
import { shouldPersistPosOrderLocally } from "@pba_pos_ux/utils/order_authority";
import { patch } from "@web/core/utils/patch";

patch(DataServiceOptions.prototype, {
    get databaseTable() {
        const tables = super.databaseTable;
        return {
            ...tables,
            "pos.order": {
                ...tables["pos.order"],
                condition: (record) => !shouldPersistPosOrderLocally(record),
            },
            "pos.order.line": {
                ...tables["pos.order.line"],
                condition: (record) =>
                    !shouldPersistPosOrderLocally(record.order_id),
            },
            "pos.payment": {
                ...tables["pos.payment"],
                condition: (record) =>
                    !shouldPersistPosOrderLocally(record.pos_order_id),
            },
            "pos.pack.operation.lot": {
                ...tables["pos.pack.operation.lot"],
                condition: (record) =>
                    !shouldPersistPosOrderLocally(
                        record.pos_order_line_id?.order_id
                    ),
            },
            "product.attribute.custom.value": {
                ...tables["product.attribute.custom.value"],
                condition: (record) => {
                    const line = record.models["pos.order.line"].find((orderLine) => {
                        const customAttrIds = orderLine.custom_attribute_value_ids.map(
                            (value) => value.id
                        );
                        return customAttrIds.includes(record.id);
                    });
                    return !shouldPersistPosOrderLocally(line?.order_id);
                },
            },
        };
    },
});
