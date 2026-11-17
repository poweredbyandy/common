from odoo import models


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def get_paperformat(self):
        paperformat = super().get_paperformat()
        layout = self.env.company.external_report_layout_id
        compact_layout = self.env.ref(
            "report_paperformat_compact.external_layout_letter_compact",
            raise_if_not_found=False,
        )
        if not layout or not compact_layout or layout != compact_layout:
            return paperformat
        if paperformat and paperformat.orientation == "Landscape":
            return paperformat
        return self.env.ref("report_paperformat_compact.paperformat_letter_compact")
