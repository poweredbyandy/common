# -*- coding: utf-8 -*-

from markupsafe import Markup

from odoo import api, models


class ReportEscposDemo(models.AbstractModel):
    _name = "report.report_escpos_webserial.report_escpos_demo_document"
    _description = "Demo ticket ESC/POS"

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env["res.partner"].browse(docids)
        parts = ["\x1b\x40"]
        for partner in docs:
            parts.append((partner.name or "") + "\n")
        parts.append("\n\n")
        return {
            "doc_ids": docids,
            "doc_model": "res.partner",
            "docs": docs,
            "escpos_payload": Markup("".join(parts)),
        }
