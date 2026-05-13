# -*- coding: utf-8 -*-

from markupsafe import Markup

from odoo import _, api, models
from odoo.exceptions import UserError


class ReportPickingZpl(models.AbstractModel):
    _name = "report.stock_picking_epl_webusb.report_picking_zpl"
    _description = "Etiquetas de paquetes ZPL (2844-Z u otros ZPL)"

    @api.model
    def _zpl_from_lines(self, lines, barcode_text):
        y = 20
        dy = 28
        parts = ["^XA\n", "^PW812\n", "^LL812\n", "^LH0,0\n", "^CF0,22\n"]
        for line in lines:
            if y > 620:
                break
            safe = (line or "").replace("^", " ").replace("~", " ")[:120]
            parts.append(f"^FO20,{y}^FD{safe}^FS\n")
            y += dy
        parts.append("^BY2\n")
        parts.append(f"^FO20,{y}^BCN,60,Y,N,N^FD{barcode_text[:40]}^FS\n")
        parts.append("^XZ\n")
        return "".join(parts)

    @api.model
    def _build_zpl_body(self, pickings):
        epl_report = self.env["report.stock_picking_epl_webusb.report_picking_epl"]
        chunks = []
        for picking in pickings:
            jobs = epl_report._picking_label_jobs(picking)
            if not jobs:
                raise UserError(
                    _(
                        "El albarán %s no tiene paquetes destino (result_package_id). "
                        "Indique bultos en el campo «Bultos (sin empaquetar)» o empaquete las líneas."
                    )
                    % (picking.display_name,)
                )
            for package, index, total in jobs:
                lines = epl_report._label_plain_lines(
                    picking, package, index, total
                )
                if package:
                    bc = (package.display_name or picking.display_name or "0")[:40]
                else:
                    bc = (picking._epl_label_scan_text() or picking.display_name or "0")[
                        :40
                    ]
                bc = "".join(c for c in bc if ord(c) < 127)
                chunks.append(self._zpl_from_lines(lines, bc))
        return "".join(chunks)

    @api.model
    def _get_report_values(self, docids, data=None):
        if not docids:
            raise UserError(_("No se indicaron albaranes para el informe ZPL."))
        pickings = self.env["stock.picking"].browse(docids)
        if not pickings:
            raise UserError(_("No se encontraron albaranes para el informe ZPL."))
        zpl_body = self._build_zpl_body(pickings)
        return {
            "doc_ids": docids,
            "doc_model": "stock.picking",
            "docs": pickings,
            "zpl_body": Markup(zpl_body),
        }
