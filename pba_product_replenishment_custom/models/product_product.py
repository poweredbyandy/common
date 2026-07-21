from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    pba_last_purchase_partner_id = fields.Many2one(
        "res.partner",
        string="Proveedor (última compra)",
        compute="_compute_pba_last_purchase_info",
    )
    pba_last_purchase_date = fields.Date(
        string="Fecha última compra",
        compute="_compute_pba_last_purchase_info",
    )
    pba_last_purchase_qty = fields.Float(
        string="Cantidad (última compra)",
        compute="_compute_pba_last_purchase_info",
        digits="Product Unit of Measure",
    )

    def _pba_get_last_purchase_lines_map(self):
        result = {}
        if not self:
            return result
        lines = self.env["purchase.order.line"].search(
            [
                ("product_id", "in", self.ids),
                ("state", "in", ("purchase", "done")),
                ("display_type", "=", False),
            ],
            order="date_approve desc, date_order desc, id desc",
        )
        for line in lines:
            pid = line.product_id.id
            if pid not in result:
                result[pid] = line
        return result

    @api.depends()
    def _compute_pba_last_purchase_info(self):
        lines_by_product = self._pba_get_last_purchase_lines_map()
        for product in self:
            line = lines_by_product.get(product.id)
            if not line:
                product.pba_last_purchase_partner_id = False
                product.pba_last_purchase_date = False
                product.pba_last_purchase_qty = 0.0
                continue
            product.pba_last_purchase_partner_id = line.partner_id
            line_dt = line.date_approve or line.date_order
            if line_dt:
                product.pba_last_purchase_date = fields.Date.to_date(line_dt)
            else:
                product.pba_last_purchase_date = False
            if line.product_uom and product.uom_id:
                product.pba_last_purchase_qty = line.product_uom._compute_quantity(
                    line.product_qty,
                    product.uom_id,
                    round=False,
                )
            else:
                product.pba_last_purchase_qty = line.product_qty or 0.0
