import logging
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.tools.float_utils import float_compare, float_is_zero

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    credit_note_return_picking_ids = fields.One2many(
        "stock.picking",
        "credit_note_move_id",
        string="Albaranes de devolución",
        copy=False,
    )

    def _post(self, soft=True):
        posted = super()._post(soft=soft)
        if self.env.context.get("skip_credit_note_return_picking"):
            return posted
        credit_notes = posted.filtered(
            lambda move: move.move_type == "out_refund" and move.state == "posted"
        )
        credit_notes._create_return_pickings_from_credit_note()
        return posted

    def _create_return_pickings_from_credit_note(self):
        for move in self:
            try:
                move._process_credit_note_stock_impact()
            except Exception:
                _logger.exception(
                    "Error creating stock impact for credit note %s",
                    move.name or move.id,
                )
                raise

    def _get_credit_note_return_picking_type(self, picking=False):
        """Prefer the original operation's return type, then company fallback."""
        self.ensure_one()
        if picking and picking.picking_type_id.return_picking_type_id:
            return picking.picking_type_id.return_picking_type_id
        return self.company_id.pba_credit_note_return_picking_type_id

    def _process_credit_note_stock_impact(self):
        self.ensure_one()
        if self.credit_note_return_picking_ids:
            return

        self._ensure_deliveries_done_for_credit_note()
        qty_by_stock_move = self._get_credit_note_return_qty_by_stock_move()
        created_pickings = self.env["stock.picking"]

        if qty_by_stock_move:
            pickings_qty = defaultdict(dict)
            for stock_move, qty in qty_by_stock_move.items():
                if not stock_move.picking_id:
                    continue
                pickings_qty[stock_move.picking_id][stock_move] = qty
            for picking, move_qty_map in pickings_qty.items():
                return_picking = self._create_return_picking_for_delivery(
                    picking, move_qty_map
                )
                if return_picking:
                    created_pickings |= return_picking

        pending_reduced = self._reduce_pending_deliveries_from_credit_note(
            qty_by_stock_move
        )

        messages = []
        if created_pickings:
            messages.append(
                _(
                    "Se generaron albaranes de devolucion: %(pickings)s",
                    pickings=", ".join(
                        "%s (%s)" % (p.name, p.picking_type_id.display_name)
                        for p in created_pickings
                    ),
                )
            )
        if pending_reduced:
            messages.append(
                _(
                    "Se ajustó la cantidad pedida y se cancelaron/redujeron "
                    "entregas pendientes por la nota de crédito."
                )
            )
        if messages:
            self.message_post(body="<br/>".join(messages))
        elif self._credit_note_has_stockable_lines():
            _logger.info(
                "Credit note %s posted without stock impact "
                "(no sale lines / no returnable qty).",
                self.name or self.id,
            )

    def _credit_note_has_stockable_lines(self):
        self.ensure_one()
        return bool(
            self.invoice_line_ids.filtered(
                lambda line: line.display_type == "product"
                and line.product_id
                and line.product_id.type == "consu"
            )
        )

    def _get_credit_note_sale_lines(self, invoice_line):
        self.ensure_one()
        sale_lines = invoice_line.sale_line_ids.filtered(
            lambda sol: sol.product_id == invoice_line.product_id
        )
        if sale_lines:
            return sale_lines
        if not self.reversed_entry_id:
            return sale_lines
        return self.reversed_entry_id.invoice_line_ids.filtered(
            lambda line: line.display_type == "product"
            and line.product_id == invoice_line.product_id
        ).sale_line_ids.filtered(
            lambda sol: sol.product_id == invoice_line.product_id
        )

    def _get_done_outgoing_moves_for_sale_line(self, sale_line):
        outgoing_moves, _incoming_moves = sale_line._get_outgoing_incoming_moves()
        done_outgoing = outgoing_moves.filtered(lambda sm: sm.state == "done")
        if done_outgoing:
            return done_outgoing
        return sale_line.move_ids.filtered(
            lambda sm: sm.state == "done"
            and not sm.scrapped
            and not sm.origin_returned_move_id
            and sm.picking_id
            and sm.location_dest_id.usage in ("customer", "transit")
        )

    def _get_pending_outgoing_moves_for_sale_line(self, sale_line):
        return sale_line.move_ids.filtered(
            lambda sm: sm.state not in ("done", "cancel")
            and not sm.scrapped
            and not sm.origin_returned_move_id
            and sm.location_dest_id.usage in ("customer", "transit")
        )

    def _ensure_deliveries_done_for_credit_note(self):
        """Force-done pending outgoing qty so a real return picking can be created."""
        self.ensure_one()
        qty_by_sale_line = self._get_credit_note_qty_by_sale_line()
        pickings_to_validate = self.env["stock.picking"]
        for sale_line, credited_qty in qty_by_sale_line.items():
            rounding = sale_line.product_uom.rounding
            done_qty = 0.0
            for stock_move in self._get_done_outgoing_moves_for_sale_line(sale_line):
                done_qty += stock_move.product_id.uom_id._compute_quantity(
                    self._get_remaining_returnable_qty(stock_move),
                    sale_line.product_uom,
                )
            missing = credited_qty - done_qty
            if float_compare(missing, 0, precision_rounding=rounding) <= 0:
                continue
            pending_moves = self._get_pending_outgoing_moves_for_sale_line(
                sale_line
            ).sorted("id")
            for stock_move in pending_moves:
                if float_compare(missing, 0, precision_rounding=rounding) <= 0:
                    break
                move_qty = stock_move.product_uom._compute_quantity(
                    stock_move.product_uom_qty, sale_line.product_uom
                )
                take = min(move_qty, missing)
                take_in_move_uom = sale_line.product_uom._compute_quantity(
                    take, stock_move.product_uom
                )
                if float_compare(
                    move_qty, take, precision_rounding=rounding
                ) > 0:
                    stock_move.write({"product_uom_qty": take_in_move_uom})
                stock_move.write({
                    "quantity": take_in_move_uom,
                    "picked": True,
                })
                if stock_move.picking_id:
                    pickings_to_validate |= stock_move.picking_id
                missing -= take
        for picking in pickings_to_validate.filtered(lambda p: p.state != "done"):
            picking = picking.with_context(
                cancel_backorder=True,
                skip_backorder=True,
                skip_sms=True,
            )
            if picking.state == "draft":
                picking.action_confirm()
            picking.move_ids.filtered(
                lambda m: m.state not in ("done", "cancel") and m.picked
            )._action_done()
            if picking.state != "done":
                picking._action_done()

    def _get_credit_note_return_qty_by_stock_move(self):
        self.ensure_one()
        qty_by_stock_move = defaultdict(float)
        product_lines = self.invoice_line_ids.filtered(
            lambda line: line.display_type == "product"
            and line.product_id
            and line.product_id.type == "consu"
            and not any(line.sale_line_ids.mapped("is_downpayment"))
        )
        for line in product_lines:
            remaining = line.product_uom_id._compute_quantity(
                abs(line.quantity), line.product_id.uom_id
            )
            rounding = line.product_id.uom_id.rounding
            if float_is_zero(remaining, precision_rounding=rounding):
                continue
            for sale_line in self._get_credit_note_sale_lines(line):
                if float_is_zero(remaining, precision_rounding=rounding):
                    break
                for stock_move in self._get_done_outgoing_moves_for_sale_line(sale_line):
                    available = self._get_remaining_returnable_qty(stock_move)
                    available -= qty_by_stock_move[stock_move]
                    if float_compare(available, 0, precision_rounding=rounding) <= 0:
                        continue
                    take = min(available, remaining)
                    qty_by_stock_move[stock_move] += take
                    remaining -= take
                    if float_is_zero(remaining, precision_rounding=rounding):
                        break
        return qty_by_stock_move

    def _get_credit_note_qty_by_sale_line(self):
        self.ensure_one()
        qty_by_sale_line = defaultdict(float)
        product_lines = self.invoice_line_ids.filtered(
            lambda line: line.display_type == "product"
            and line.product_id
            and line.product_id.type == "consu"
            and not any(line.sale_line_ids.mapped("is_downpayment"))
        )
        for line in product_lines:
            remaining = abs(line.quantity)
            rounding = line.product_uom_id.rounding
            if float_is_zero(remaining, precision_rounding=rounding):
                continue
            sale_lines = self._get_credit_note_sale_lines(line)
            if not sale_lines:
                continue
            share = remaining / len(sale_lines)
            for sale_line in sale_lines:
                qty_by_sale_line[sale_line] += line.product_uom_id._compute_quantity(
                    share, sale_line.product_uom, rounding_method="HALF-UP"
                )
        return qty_by_sale_line

    def _reduce_pending_deliveries_from_credit_note(self, qty_by_done_stock_move):
        self.ensure_one()
        done_qty_by_sale_line = defaultdict(float)
        for stock_move, qty in qty_by_done_stock_move.items():
            if stock_move.sale_line_id:
                done_qty_by_sale_line[stock_move.sale_line_id] += (
                    stock_move.product_id.uom_id._compute_quantity(
                        qty, stock_move.sale_line_id.product_uom
                    )
                )

        qty_by_sale_line = self._get_credit_note_qty_by_sale_line()
        touched = False
        for sale_line, credited_qty in qty_by_sale_line.items():
            rounding = sale_line.product_uom.rounding
            already_returned = done_qty_by_sale_line.get(sale_line, 0.0)
            pending_to_reduce = credited_qty - already_returned
            if float_compare(pending_to_reduce, 0, precision_rounding=rounding) <= 0:
                continue
            reduced = self._reduce_sale_line_pending_qty(sale_line, pending_to_reduce)
            if float_compare(reduced, 0, precision_rounding=rounding) > 0:
                touched = True
        return touched

    def _reduce_sale_line_pending_qty(self, sale_line, qty_to_reduce):
        rounding = sale_line.product_uom.rounding
        remaining = qty_to_reduce
        pending_moves = self._get_pending_outgoing_moves_for_sale_line(sale_line).sorted(
            "id", reverse=True
        )
        for stock_move in pending_moves:
            if float_compare(remaining, 0, precision_rounding=rounding) <= 0:
                break
            move_qty = stock_move.product_uom._compute_quantity(
                stock_move.product_uom_qty, sale_line.product_uom
            )
            if float_compare(move_qty, remaining, precision_rounding=rounding) <= 0:
                remaining -= move_qty
                stock_move._action_cancel()
            else:
                new_qty = move_qty - remaining
                stock_move.write({
                    "product_uom_qty": sale_line.product_uom._compute_quantity(
                        new_qty, stock_move.product_uom
                    ),
                })
                if float_compare(
                    stock_move.quantity,
                    stock_move.product_uom_qty,
                    precision_rounding=stock_move.product_uom.rounding,
                ) > 0:
                    stock_move.quantity = stock_move.product_uom_qty
                remaining = 0.0

        reduced = qty_to_reduce - max(remaining, 0.0)
        reduce_ordered = qty_to_reduce
        new_ordered = max(sale_line.product_uom_qty - reduce_ordered, 0.0)
        if float_compare(
            sale_line.product_uom_qty, new_ordered, precision_rounding=rounding
        ) != 0:
            order = sale_line.order_id
            was_locked = order.locked
            if was_locked:
                order.locked = False
            sale_line.with_context(skip_procurement=True).write({
                "product_uom_qty": new_ordered,
            })
            if was_locked:
                order.locked = True
            reduced = max(reduced, reduce_ordered)
        return reduced

    @api.model
    def _get_remaining_returnable_qty(self, stock_move):
        rounding = stock_move.product_id.uom_id.rounding
        qty = stock_move.product_uom._compute_quantity(
            stock_move.quantity, stock_move.product_id.uom_id
        )
        returned_moves = stock_move.returned_move_ids.filtered(
            lambda sm: sm.state != "cancel"
        )
        for returned in returned_moves:
            returned_qty = (
                returned.quantity if returned.state == "done" else returned.product_uom_qty
            )
            qty -= returned.product_uom._compute_quantity(
                returned_qty, stock_move.product_id.uom_id
            )
        if float_compare(qty, 0, precision_rounding=rounding) <= 0:
            return 0.0
        return qty

    def _create_return_picking_for_delivery(self, picking, move_qty_map, return_type=False):
        self.ensure_one()
        if not picking or not picking._can_return():
            return self.env["stock.picking"]
        return_type = return_type or self._get_credit_note_return_picking_type(picking)
        wizard_ctx = {
            "active_id": picking.id,
            "active_ids": picking.ids,
            "active_model": "stock.picking",
        }
        if return_type:
            wizard_ctx["pba_credit_note_return_picking_type"] = return_type
        wizard = self.env["stock.return.picking"].with_context(**wizard_ctx).create({
            "picking_id": picking.id,
        })
        has_qty = False
        for wizard_line in wizard.product_return_moves:
            qty = move_qty_map.get(wizard_line.move_id, 0.0)
            vals = {"quantity": qty}
            if "to_refund" in wizard_line._fields:
                vals["to_refund"] = True
            wizard_line.write(vals)
            if not float_is_zero(
                qty, precision_rounding=wizard_line.product_id.uom_id.rounding
            ):
                has_qty = True
        if not has_qty:
            return self.env["stock.picking"]
        action = wizard.action_create_returns()
        return_picking = self.env["stock.picking"].browse(action.get("res_id"))
        if not return_picking:
            return self.env["stock.picking"]
        vals = {
            "credit_note_move_id": self.id,
            "origin": _(
                "Return of %(picking)s / %(credit_note)s",
                picking=picking.name,
                credit_note=self.name,
            ),
        }
        if return_type:
            vals["picking_type_id"] = return_type.id
            if return_type.default_location_dest_id:
                vals["location_dest_id"] = return_type.default_location_dest_id.id
            if picking.location_dest_id:
                vals["location_id"] = picking.location_dest_id.id
        return_picking.write(vals)
        return return_picking
