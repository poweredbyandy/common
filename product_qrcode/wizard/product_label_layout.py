from odoo import _, fields, models
from odoo.exceptions import UserError


class ProductLabelLayout(models.TransientModel):
    _inherit = "product.label.layout"

    print_format = fields.Selection(
        selection_add=[
            ("qr_label_code", "ZPL QR (product code)"),
        ],
        ondelete={"qr_label_code": "set default"},
    )

    def _prepare_report_data(self):
        self.ensure_one()
        if self.print_format == "qr_label_code":
            if self.custom_quantity <= 0:
                raise UserError(_("You need to set a positive quantity."))
            if self.product_tmpl_ids:
                products = self.product_tmpl_ids.mapped("product_variant_ids")
                active_model = "product.template"
                product_keys = self.product_tmpl_ids.ids
            elif self.product_ids:
                products = self.product_ids
                active_model = "product.product"
                product_keys = self.product_ids.ids
            else:
                raise UserError(
                    _(
                        "No product to print. If the product is archived, "
                        "unarchive it before printing its label."
                    )
                )
            if not products:
                raise UserError(_("No product variants found to print."))
            data = {
                "active_model": active_model,
                "layout_wizard": self.id,
                "quantity_by_product": {
                    str(product_id): self.custom_quantity for product_id in product_keys
                },
                "zpl_qr_mode": "product",
            }
            return "product_qrcode.action_report_product_qr_zpl", data
        return super()._prepare_report_data()
