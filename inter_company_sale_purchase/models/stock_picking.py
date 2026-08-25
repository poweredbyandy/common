from odoo import Command, api, models


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        res = super().button_validate()
        if self.env.context.get("skip_ic_picking_sync"):
            return res
        for picking in self:
            picking._ic_sync_counterpart_picking()
        return res

    def _ic_sync_counterpart_picking(self):
        self.ensure_one()
        if self.state != "done":
            return
        if not self.sale_id or self.picking_type_code not in ("outgoing", "dropship"):
            return
        company = self.env["res.company"]._find_company_from_partner(self.sale_id.partner_id.id)
        if not company or company.ic_picking_mode == "none":
            return
        rights = ["stock", "purchase"]
        ic_user = company._ic_ensure_user(rights)
        sale_order = self.sale_id.sudo()
        purchase_order = sale_order.auto_purchase_order_id
        if not purchase_order:
            purchase_order = (
                self.env["purchase.order"]
                .sudo()
                .search(
                    [
                        ("name", "=", sale_order.client_order_ref),
                        ("company_id", "=", company.id),
                    ],
                    limit=1,
                )
            )
        if not purchase_order:
            return
        receipts = purchase_order.picking_ids.sudo().filtered(
            lambda picking: picking.picking_type_code in ("incoming", "dropship")
            and picking.state not in ("done", "cancel")
        )
        if not receipts:
            return
        for move in self.move_ids:
            if move.state != "done":
                continue
            if move.product_id.company_id:
                continue
            receipt_move = self._ic_find_corresponding_move(move, receipts)
            if not receipt_move:
                continue
            receipt_move.sudo().write(
                {
                    "move_line_ids": [
                        *[Command.delete(line.id) for line in receipt_move.move_line_ids],
                        *[
                            Command.create(vals)
                            for vals in self._ic_prepare_move_lines(move, receipt_move)
                        ],
                    ]
                }
            )
            receipt_move.sudo().move_line_ids._apply_putaway_strategy()
        if company.ic_picking_mode == "validate":
            receipts_to_validate = receipts.filtered(
                lambda picking: picking.state not in ("done", "cancel")
            )
            if receipts_to_validate:
                receipts_to_validate.with_user(ic_user).with_company(company).with_context(
                    skip_ic_picking_sync=True,
                    skip_backorder=True,
                    skip_sms=True,
                    allowed_company_ids=company.ids,
                ).sudo().button_validate()

    @api.model
    def _ic_find_corresponding_move(self, move_orig, candidate_pickings):
        for move in candidate_pickings.move_ids:
            if move.product_id == move_orig.product_id and not move.picked:
                return move
        return self.env["stock.move"]

    @api.model
    def _ic_prepare_move_lines(self, delivery_move, receipt_move):
        move_lines_vals = []
        for move_line in delivery_move.move_line_ids:
            vals = receipt_move._prepare_move_line_vals(quantity=0)
            if move_line.lot_id:
                vals["lot_name"] = move_line.lot_id.name
                if not move_line.lot_id.company_id:
                    vals["lot_id"] = move_line.lot_id.id
            vals["quantity"] = move_line.quantity
            vals["picked"] = True
            move_lines_vals.append(vals)
        return move_lines_vals
