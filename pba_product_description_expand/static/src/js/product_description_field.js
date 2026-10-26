/** @odoo-module **/

import { registry } from "@web/core/registry";
import { TextField, textField } from "@web/views/fields/text/text_field";

const LINE_HEIGHT = 24;

export class ProductDescriptionField extends TextField {
    get minimumHeight() {
        // The text widget autoresizes from the content and ignores a tall
        // `rows` value, so the description collapses back to two lines.
        return Math.max(super.minimumHeight, this.rowCount * LINE_HEIGHT);
    }
}

registry.category("fields").add("pba_product_description", {
    ...textField,
    component: ProductDescriptionField,
});
