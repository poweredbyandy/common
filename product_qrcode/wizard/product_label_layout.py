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

    def _get_qr_label_stock_report_data(self):
        self.ensure_one()
        move_quantity = getattr(self, "move_quantity", "custom")
        move_ids = getattr(self, "move_ids", self.env["stock.move"])
        if move_quantity == "move" and move_ids:
            _xml_id, data = super()._prepare_report_data()
            return data
        return {}

    def _qr_label_has_printable_stock_data(self, product_keys, stock_data):
        qty_map = stock_data.get("quantity_by_product") or {}
        custom_barcodes = stock_data.get("custom_barcodes") or {}
        for product_id in product_keys:
            product_key = str(product_id)
            if qty_map.get(product_id) or qty_map.get(product_key):
                return True
            if custom_barcodes.get(product_id) or custom_barcodes.get(int(product_id)):
                return True
        return False

    def _get_qr_label_quantity_by_product(self, product_keys):
        self.ensure_one()
        stock_data = self._get_qr_label_stock_report_data()
        if stock_data:
            qty_map = stock_data.get("quantity_by_product") or {}
            quantities = {}
            for product_id in product_keys:
                qty = qty_map.get(product_id)
                if qty is None:
                    qty = qty_map.get(str(product_id), 0)
                if qty:
                    quantities[str(product_id)] = int(qty)
            if quantities or self._qr_label_has_printable_stock_data(
                product_keys, stock_data
            ):
                return quantities
            raise UserError(_("No quantity to print from the selected operations."))
        if self.custom_quantity <= 0:
            raise UserError(_("You need to set a positive quantity."))
        return {str(product_id): self.custom_quantity for product_id in product_keys}

    def _prepare_qr_label_report_data(self, zpl_qr_mode, extra_data=None):
        self.ensure_one()
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
        stock_data = self._get_qr_label_stock_report_data()
        data = {
            "active_model": active_model,
            "layout_wizard": self.id,
            "quantity_by_product": self._get_qr_label_quantity_by_product(
                product_keys
            ),
            "zpl_qr_mode": zpl_qr_mode,
        }
        custom_barcodes = stock_data.get("custom_barcodes")
        if custom_barcodes:
            data["custom_barcodes"] = custom_barcodes
        if extra_data:
            data.update(extra_data)
        return data

    def _prepare_report_data(self):
        self.ensure_one()
        if self.print_format == "qr_label_code":
            data = self._prepare_qr_label_report_data("product")
            return "product_qrcode.action_report_product_qr_zpl", data
        return super()._prepare_report_data()
