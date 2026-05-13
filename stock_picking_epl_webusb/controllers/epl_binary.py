# -*- coding: utf-8 -*-

import base64
import io

from odoo import http
from odoo.exceptions import AccessError, UserError
from odoo.http import request


class StockPickingEplWebusbBinary(http.Controller):
    @http.route(
        "/stock_picking_epl_webusb/epl_picking_binary",
        type="http",
        auth="user",
        methods=["GET"],
        readonly=True,
        csrf=False,
    )
    def epl_picking_binary(self, docids=None, **kwargs):
        if not docids:
            return request.not_found()
        ids = []
        for part in docids.split(","):
            part = part.strip()
            if part.isdigit():
                ids.append(int(part))
        if not ids:
            return request.not_found()
        pickings = request.env["stock.picking"].browse(ids)
        if not pickings or len(pickings) != len(ids):
            return request.not_found()
        try:
            pickings.check_access("read")
        except AccessError:
            return request.make_response("Forbidden", status=403)
        report = request.env["report.stock_picking_epl_webusb.report_picking_epl"]
        try:
            body = report._render_epl_webusb_binary_body(pickings)
        except UserError as e:
            return request.make_response(
                (e.args[0] if e.args else "Error").encode("utf-8"),
                status=400,
                headers=[("Content-Type", "text/plain; charset=utf-8")],
            )
        return request.make_response(
            body,
            headers=[
                ("Content-Type", "application/octet-stream"),
                ("Content-Disposition", 'attachment; filename="picking-packages.epl"'),
            ],
        )
