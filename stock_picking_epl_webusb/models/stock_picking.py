# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    dispatch_bultos_manual = fields.Integer(
        string="Bultos (sin empaquetar)",
        default=0,
        copy=False,
        help="Si no hay paquetes destino en las operaciones, indique cuántas etiquetas EPL/ZPL desea imprimir por WebUSB.",
    )

    @api.constrains("dispatch_bultos_manual")
    def _check_dispatch_bultos_manual(self):
        for picking in self:
            if picking.dispatch_bultos_manual < 0:
                raise ValidationError(_("Los bultos manuales no pueden ser negativos."))

    def _epl_label_scan_text(self):
        self.ensure_one()
        if "barcode" in self._fields:
            bc = (self.barcode or "").strip()
            if bc:
                return bc
        return (self.name or "").strip()

    def _dispatch_out_invoices(self, moves):
        return moves.filtered(
            lambda move: move.move_type == "out_invoice" and move.state != "cancel"
        )

    def _dispatch_open_moves(self):
        return self.move_ids.filtered(lambda move: move.state != "cancel")

    def _dispatch_invoice_product_lines(self, invoice):
        return invoice.invoice_line_ids.filtered(
            lambda line: line.display_type == "product"
        )

    def _dispatch_invoice_match_score(self, invoice):
        self.ensure_one()
        moves = self._dispatch_open_moves()
        picking_products = moves.mapped("product_id")
        picking_lines = (
            moves.mapped("sale_line_id")
            if "sale_line_id" in moves._fields
            else self.env["stock.move"].browse()
        )
        inv_lines = self._dispatch_invoice_product_lines(invoice)
        invoice_products = inv_lines.mapped("product_id")
        invoice_sale_lines = (
            inv_lines.mapped("sale_line_ids")
            if "sale_line_ids" in inv_lines._fields
            else self.env["stock.move"].browse()
        )
        picking_qty = {}
        for move in moves:
            qty = move.quantity if move.quantity else move.product_uom_qty
            picking_qty[move.product_id.id] = (
                picking_qty.get(move.product_id.id, 0.0) + qty
            )
        invoice_qty = {}
        for line in inv_lines:
            invoice_qty[line.product_id.id] = (
                invoice_qty.get(line.product_id.id, 0.0) + line.quantity
            )
        qty_diff = 0.0
        for product_id in set(picking_qty) | set(invoice_qty):
            qty_diff += abs(
                picking_qty.get(product_id, 0.0) - invoice_qty.get(product_id, 0.0)
            )
        return (
            len(picking_products & invoice_products),
            len(picking_lines & invoice_sale_lines),
            -len(invoice_products - picking_products),
            -len(picking_products - invoice_products),
            -qty_diff,
        )

    def _dispatch_invoices_matching(self):
        self.ensure_one()
        moves = self._dispatch_open_moves()
        if "sale_line_id" not in moves._fields:
            return self.env["account.move"]
        sale_lines = moves.mapped("sale_line_id")
        if not sale_lines or "invoice_lines" not in sale_lines._fields:
            return self.env["account.move"]
        invoices = self._dispatch_out_invoices(sale_lines.mapped("invoice_lines.move_id"))
        picking_products = moves.mapped("product_id")
        return invoices.filtered(
            lambda invoice: bool(
                self._dispatch_invoice_product_lines(invoice).mapped("product_id")
                & picking_products
            )
        )

    def _dispatch_choose_invoice(self, invoices):
        self.ensure_one()
        if not invoices:
            return invoices
        if len(invoices) == 1:
            return invoices
        scored = invoices.sorted(
            key=lambda invoice: self._dispatch_invoice_match_score(invoice),
            reverse=True,
        )
        best_score = self._dispatch_invoice_match_score(scored[0])
        tied = invoices.filtered(
            lambda invoice: self._dispatch_invoice_match_score(invoice) == best_score
        )
        if len(tied) == 1:
            return tied
        tied = tied.sorted("id")
        siblings = self
        if "sale_id" in self._fields and self.sale_id:
            siblings = self.sale_id.picking_ids.filtered(
                lambda rec: rec.state != "cancel" and rec.picking_type_code == "outgoing"
            ).sorted("id")
        matching_siblings = siblings.filtered(
            lambda rec: rec._dispatch_invoice_match_score(tied[0]) == best_score
        )
        if self in matching_siblings:
            index = list(matching_siblings.ids).index(self.id)
            if index < len(tied):
                return tied[index]
        return tied[0]

    def _dispatch_invoice_for_picking(self):
        self.ensure_one()
        linked = self.env["account.move"]
        if "invoice_ids" in self._fields and self.invoice_ids:
            linked = self._dispatch_out_invoices(self.invoice_ids)
        matched = self._dispatch_invoices_matching()
        candidates = linked | matched
        if not candidates:
            return self.env["account.move"]
        return self._dispatch_choose_invoice(candidates)

    def _dispatch_invoice_ref(self):
        self.ensure_one()
        invoice = self._dispatch_invoice_for_picking()
        if invoice:
            return invoice.name or invoice.payment_reference or ""
        return self.origin or ""
