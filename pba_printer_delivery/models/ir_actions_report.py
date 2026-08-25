from odoo import models

POS80_REPORT_NAME = "pba_printer_delivery.pos80_ticket_doc"


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _render_qweb_text(self, report_ref, docids, data=None):
        report = self._get_report(report_ref)
        if report.report_name == POS80_REPORT_NAME:
            pickings = self.env["stock.picking"].browse(docids)
            return (
                b"".join(picking._pba_pos80_ticket_bytes() for picking in pickings),
                "text",
            )
        return super()._render_qweb_text(report_ref, docids, data=data)
