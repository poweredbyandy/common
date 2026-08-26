from odoo import api, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.model
    def _get_barcode_used_lot_names(self, product):
        used_names = set(
            self.move_line_ids.filtered(
                lambda line: line.product_id == product and line.lot_name
            ).mapped("lot_name")
        )
        used_names.update(
            self.move_line_ids.filtered(
                lambda line: line.product_id == product and line.lot_id
            ).mapped("lot_id.name")
        )
        return used_names

    @api.model
    def _get_barcode_default_lot_name(self, product):
        lot_name = self.env["stock.lot"]._get_next_serial(self.company_id, product)
        if lot_name:
            return lot_name
        prefix = product.default_code or "LOT"
        return self.env["stock.lot"].generate_lot_names("%s00001" % prefix, 1)[0][
            "lot_name"
        ]

    def get_barcode_next_lot_name(self, product_id):
        self.ensure_one()
        product = self.env["product.product"].browse(product_id).exists()
        if not product or product.tracking == "none":
            return False
        picking_type = self.picking_type_id
        if not picking_type.use_create_lots and not picking_type.use_existing_lots:
            return False
        lot_name = self._get_barcode_default_lot_name(product)
        used_names = self._get_barcode_used_lot_names(product)
        while lot_name in used_names:
            lot_name = self.env["stock.lot"].generate_lot_names(lot_name, 2)[1][
                "lot_name"
            ]
        return lot_name
