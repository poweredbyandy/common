from odoo import http
from odoo.addons.stock_barcode.controllers.stock_barcode import StockBarcodeController
from odoo.http import request


class PbaStockBarcodeController(StockBarcodeController):
    def _try_open_picking(self, barcode):
        result = super()._try_open_picking(barcode)
        if result:
            return result
        picking = request.env["stock.picking"]
        for variant in picking._pba_picking_name_barcode_variants(barcode):
            if variant == barcode:
                continue
            result = super()._try_open_picking(variant)
            if result:
                return result
        return False

    def _pba_expand_picking_barcodes_by_model(self, kwargs):
        picking = request.env["stock.picking"]
        barcodes_by_model = kwargs.get("barcodes_by_model")
        if barcodes_by_model and barcodes_by_model.get("stock.picking"):
            expanded = []
            for barcode in barcodes_by_model["stock.picking"]:
                expanded.extend(picking._pba_picking_name_barcode_variants(barcode))
            kwargs["barcodes_by_model"]["stock.picking"] = list(dict.fromkeys(expanded))
            return kwargs
        if barcodes_by_model or not (kwargs.get("barcode") or kwargs.get("barcodes")):
            return kwargs
        barcodes = kwargs.get("barcodes") or [kwargs.get("barcode")]
        field_by_model = self._get_barcode_field_by_model()
        kwargs["barcodes_by_model"] = {
            model_name: list(
                dict.fromkeys(
                    variant
                    for barcode in barcodes
                    for variant in picking._pba_picking_name_barcode_variants(barcode)
                )
            )
            if model_name == "stock.picking"
            else barcodes
            for model_name in field_by_model
        }
        return kwargs

    @http.route()
    def get_specific_barcode_data(self, **kwargs):
        kwargs = self._pba_expand_picking_barcodes_by_model(kwargs)
        return super().get_specific_barcode_data(**kwargs)
