# -*- coding: utf-8 -*-

from odoo import api, models

_KEEP_REPORT_XMLIDS = (
    "report_escpos_inventory.action_report_stock_picking_dispatch_escpos",
    "report_escpos_inventory.action_report_stock_picking_dispatch_pdf",
    "report_escpos_inventory.action_report_stock_picking_escp_test",
)


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _report_escpos_inventory_keep_reports(self):
        reports = self.env["ir.actions.report"]
        for xmlid in _KEEP_REPORT_XMLIDS:
            report = self.env.ref(xmlid, raise_if_not_found=False)
            if report:
                reports |= report
        return reports

    @api.model
    def _report_escpos_inventory_restore_picking_bindings(self):
        picking_model = self.env["ir.model"]._get("stock.picking")
        if not picking_model:
            return
        to_restore = self._report_escpos_inventory_keep_reports().filtered(
            lambda report: report.binding_model_id != picking_model
            or report.binding_type != "report"
        )
        if to_restore:
            to_restore.sudo().write(
                {
                    "binding_model_id": picking_model.id,
                    "binding_type": "report",
                }
            )

    def _register_hook(self):
        super()._register_hook()
        self._report_escpos_inventory_restore_picking_bindings()
