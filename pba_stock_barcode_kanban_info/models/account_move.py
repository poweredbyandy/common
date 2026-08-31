from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def write(self, vals):
        result = super().write(vals)
        if any(
            field_name in vals
            for field_name in (
                "invoice_payment_term_id",
                "payment_state",
                "amount_residual",
            )
        ):
            self._pba_notify_barcode_related_pickings()
        return result

    def _compute_payment_state(self):
        super()._compute_payment_state()
        self._pba_notify_barcode_related_pickings()

    def _pba_notify_barcode_related_pickings(self):
        invoices = self.filtered(
            lambda move: move.move_type in ("out_invoice", "out_refund")
        )
        if not invoices:
            return
        sales = invoices.line_ids.sale_line_ids.order_id
        sales |= self.env["sale.order"].search([("invoice_ids", "in", invoices.ids)])
        pickings = sales.picking_ids
        if "picking_ids" in invoices._fields:
            pickings |= invoices.picking_ids
        else:
            invoice_field = self.env["stock.picking"]._fields.get("invoice_ids")
            if invoice_field and (invoice_field.store or invoice_field.search):
                pickings |= self.env["stock.picking"].search(
                    [("invoice_ids", "in", invoices.ids)]
                )
        if pickings:
            pickings._pba_notify_barcode_available()
        else:
            self.env["stock.picking"]._pba_bus_barcode_reload()
