# -*- coding: utf-8 -*-

from odoo import models

_DISPATCH_REPORT_XMLIDS = (
    "report_escpos_inventory.action_report_stock_picking_dispatch_escpos",
    "report_escpos_inventory.action_report_stock_picking_dispatch_pdf",
)


class AccountMove(models.Model):
    _inherit = "account.move"

    def _report_escpos_inventory_dispatch_pickings(self):
        pickings = self.env["stock.picking"]
        if "picking_ids" in self._fields:
            pickings = self.mapped("picking_ids")
        return pickings.filtered(
            lambda picking: picking.state != "cancel"
            and picking.picking_type_code == "outgoing"
        )

    def get_extra_print_items(self):
        items = super().get_extra_print_items()
        pickings = self._report_escpos_inventory_dispatch_pickings()
        if not pickings:
            return items
        extra = []
        for xmlid in _DISPATCH_REPORT_XMLIDS:
            report = self.env.ref(xmlid, raise_if_not_found=False)
            if not report:
                continue
            action = report.report_action(pickings, config=False)
            if not isinstance(action, dict) or action.get("type") != "ir.actions.report":
                continue
            extra.append(
                {
                    "key": "report_escpos_inventory_%s" % report.id,
                    "description": report.name,
                    **action,
                }
            )
        return extra + items
