from odoo import _, models
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def button_approve(self, force=False):
        res = super().button_approve(force=force)
        self.filtered(lambda o: o.state in ("purchase", "done"))._pba_apply_confirmed_line_costs_to_templates()
        return res

    def action_pba_update_sale_prices(self):
        self.ensure_one()
        vals_by_tmpl = {}
        lines_updated = self.env["purchase.order.line"]
        for line in self.order_line:
            delta = line._pba_build_template_sale_price_vals_from_line()
            if not delta:
                continue
            tid = line.product_id.product_tmpl_id.id
            vals_by_tmpl[tid] = delta
            lines_updated |= line
        if not vals_by_tmpl:
            raise UserError(
                _("No hay líneas con precio de venta PBA para actualizar en esta orden.")
            )
        for tid, vals in vals_by_tmpl.items():
            self.env["product.template"].browse(tid).write(vals)
        for line in lines_updated:
            line.write({"pba_sale_price_unit_baseline": line.pba_sale_price_unit})
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Precios de venta"),
                "message": _(
                    "Se actualizó el precio de venta de %(count)s producto(s).",
                    count=len(vals_by_tmpl),
                ),
                "type": "success",
                "sticky": False,
            },
        }

    def _pba_apply_confirmed_line_costs_to_templates(self):
        vals_by_tmpl = {}
        for line in self.order_line:
            if line.display_type or not line.product_id:
                continue
            tid = line.product_id.product_tmpl_id.id
            delta = line._pba_build_template_sync_vals_from_line()
            if not delta:
                continue
            bucket = vals_by_tmpl.setdefault(tid, {})
            bucket.update(delta)
        for tid, vals in vals_by_tmpl.items():
            if vals:
                self.env["product.template"].browse(tid).write(vals)

    def write(self, vals):
        res = super().write(vals)
        if "state" in vals:
            self.order_line.product_id.product_tmpl_id._pba_invalidate_last_cost()
        return res

    def unlink(self):
        templates = self.order_line.product_id.product_tmpl_id
        res = super().unlink()
        templates._pba_invalidate_last_cost()
        return res
