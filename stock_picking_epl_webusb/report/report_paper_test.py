# -*- coding: utf-8 -*-

from markupsafe import Markup

from odoo import api, models

LF = "\n"

EPL_PAPER_TEST = LF.join(
    [
        "N",
        "q812",
        "Q812,24",
        "rN",
        "D15",
        'A50,0,0,1,1,1,N,"Example 1"',
        'A50,50,0,2,1,1,N,"Example 2"',
        'A50,100,0,3,1,1,N,"Example 3"',
        'A50,150,0,4,1,1,N,"Example 4"',
        'A50,200,0,5,1,1,N,"EXAMPLE 5"',
        "LO30,300,750,4",
        'B40,330,0,3,2,4,70,B,"TESTOK"',
        "P1",
    ]
)


class ReportPaperTestEpl(models.AbstractModel):
    _name = "report.stock_picking_epl_webusb.report_paper_test_epl"
    _description = "Prueba de papel EPL"

    @api.model
    def _get_report_values(self, docids, data=None):
        epl = EPL_PAPER_TEST
        if not epl.endswith("\n"):
            epl += "\n"
        return {
            "doc_ids": docids or [],
            "doc_model": "stock.picking",
            "docs": self.env["stock.picking"].browse(docids or []),
            "epl_body": Markup(epl),
        }


class ReportPaperTestZpl(models.AbstractModel):
    _name = "report.stock_picking_epl_webusb.report_paper_test_zpl"
    _description = "Prueba de papel ZPL"

    @api.model
    def _get_report_values(self, docids, data=None):
        zpl = (
            "^XA\n"
            "^PW812\n"
            "^LL812\n"
            "^LH0,0\n"
            "^CF0,32\n"
            "^FO50,200^A0N,40,40^FDEXAMPLE1^FS\n"
            "^XZ\n"
        )
        return {
            "doc_ids": docids or [],
            "doc_model": "stock.picking",
            "docs": self.env["stock.picking"].browse(docids or []),
            "zpl_body": Markup(zpl),
        }
