# -*- coding: utf-8 -*-

import json

from odoo import http
from odoo.http import request


class ReportEscposController(http.Controller):
    @http.route(
        [
            "/report/escpos/<string:reportname>",
            "/report/escpos/<string:reportname>/<string:docids>",
        ],
        type="http",
        auth="user",
        website=True,
        readonly=True,
    )
    def report_escpos_routes(self, reportname, docids=None, **data):
        report = request.env["ir.actions.report"]
        context = dict(request.env.context)

        if docids:
            docids = [int(i) for i in docids.split(",") if i.isdigit()]
        if data.get("options"):
            data.update(json.loads(data.pop("options")))
        if data.get("context"):
            data["context"] = json.loads(data["context"])
            context.update(data["context"])

        payload = report.with_context(context)._render_qweb_escpos(
            reportname, docids, data=data
        )[0]

        headers = [
            ("Content-Type", "application/octet-stream"),
            ("Content-Length", len(payload)),
        ]
        return request.make_response(payload, headers=headers)
