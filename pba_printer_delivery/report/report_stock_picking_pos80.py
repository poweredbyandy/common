from odoo import api, models

REPORT_NAME = "pba_printer_delivery.pos80_ticket_doc"


class ReportStockPickingPos80(models.AbstractModel):
    _name = "report.pba_printer_delivery.pos80_ticket_doc"
    _description = "POS-80 delivery ticket"

    @api.model
    def _get_report_values(self, docids, data=None):
        pickings = self.env["stock.picking"].browse(docids)
        return {
            "doc_ids": docids,
            "doc_model": "stock.picking",
            "docs": pickings,
        }
