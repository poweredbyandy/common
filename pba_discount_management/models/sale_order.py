from odoo import _, api, fields, models
from odoo.tools.float_utils import float_is_zero


class SaleOrder(models.Model):
    _inherit = "sale.order"

    pba_discount_legacy = fields.Boolean(
        string="PBA Legacy Discount",
        default=False,
        copy=False,
        help="When set, global discounts use a negative discount product line "
        "(legacy PBA mode). New documents use l10n_ve_seniat global discounts.",
    )
    pba_document_discount_percent = fields.Float(
        string="% Descuento (documento)",
        compute="_compute_pba_document_discount_percent",
        digits="Discount",
    )

    @api.depends(
        "order_line.price_subtotal",
        "order_line.product_id",
        "order_line.display_type",
        "amount_untaxed",
        "pba_discount_legacy",
        "l10n_ve_global_discount_ids.amount",
        "l10n_ve_global_discount_ids.discount_type",
        "l10n_ve_global_discount_ids.discount_percentage",
    )
    def _compute_pba_document_discount_percent(self):
        prec = self.env["decimal.precision"].precision_get("Discount")
        for order in self:
            if order.pba_discount_legacy:
                product_lines = order.order_line.filtered(
                    lambda line: not line._is_discount_line()
                    and line.display_type not in ("line_section", "line_note")
                )
            else:
                disc = order.company_id.sale_discount_product_id
                product_lines = order.order_line.filtered(
                    lambda line: line.display_type not in ("line_section", "line_note")
                    and not line._is_discount_line()
                    and (not disc or line.product_id != disc)
                )
            und = sum(product_lines.mapped("price_subtotal"))
            if float_is_zero(und, precision_digits=prec):
                order.pba_document_discount_percent = 0.0
            else:
                order.pba_document_discount_percent = (
                    (und - (order.amount_untaxed or 0.0)) / und * 100.0
                )

    @api.model
    def _pba_mark_legacy_discount_documents(self):
        """Mark sale orders that already have product discount lines as legacy."""
        orders = self.search([("pba_discount_legacy", "=", False)])
        to_mark = self.env["sale.order"]
        for order in orders:
            if order.l10n_ve_global_discount_ids:
                continue
            if order.order_line.filtered(lambda line: line._is_discount_line()):
                to_mark |= order
        if to_mark:
            to_mark.write({"pba_discount_legacy": True})
        return to_mark

    def _pba_mark_legacy_if_product_discount_lines(self):
        for order in self.filtered(lambda o: not o.pba_discount_legacy):
            if order.l10n_ve_global_discount_ids:
                continue
            if order.order_line.filtered(lambda line: line._is_discount_line()):
                order.pba_discount_legacy = True

    @api.constrains("order_line")
    def _pba_check_single_discount_line(self):
        policy = self.env["pba.discount.policy"]
        for order in self.filtered("pba_discount_legacy"):
            discount_lines = order.order_line.filtered(lambda line: line._is_discount_line())
            policy._pba_raise_if_multiple_discount_lines(len(discount_lines))

    def action_open_discount_wizard(self):
        self.ensure_one()
        self.env["pba.discount.policy"]._pba_require_global_discount_rights()
        if self.pba_discount_legacy:
            return {
                "name": _("Discount"),
                "type": "ir.actions.act_window",
                "res_model": "sale.order.discount",
                "view_mode": "form",
                "target": "new",
                "context": {
                    "default_sale_order_id": self.id,
                    "default_discount_type": "so_discount",
                    "active_id": self.id,
                    "active_model": "sale.order",
                },
            }
        return super().action_open_discount_wizard()
