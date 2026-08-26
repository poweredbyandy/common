from odoo import fields, models


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    barcode_block_over_demand = fields.Boolean(
        string="Block Over-Demand Scans",
        default=True,
        help="When enabled, the Barcode app rejects scans that would pick, "
        "receive, or move more units than the requested quantity on the transfer.",
    )

    def _get_barcode_config(self):
        config = super()._get_barcode_config()
        config["barcode_block_over_demand"] = self.barcode_block_over_demand
        return config
