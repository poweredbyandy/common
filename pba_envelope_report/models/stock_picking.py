from odoo import models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _envelope_bultos_count(self):
        """Real number of packages of the delivery (0 if unknown).

        1. Destination packages on the operations (same criterion used by the
           EPL/ZPL labels: "Bulto X de N").
        2. Otherwise the manual field "Bultos (sin empaquetar)" from
           stock_picking_epl_webusb, when that module is installed.
        """
        self.ensure_one()
        packages = len(self.move_line_ids.result_package_id)
        if packages:
            return packages
        if "dispatch_bultos_manual" in self._fields:
            return self.dispatch_bultos_manual or 0
        return 0

    def _envelope_bultos(self):
        self.ensure_one()
        return self._envelope_bultos_count()
