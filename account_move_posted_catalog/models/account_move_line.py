from odoo import api, models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    @api.model
    def _posted_catalog_vals_is_commercial_line(self, vals):
        """Línea que el usuario agrega desde la factura o el catálogo.

        Las líneas automáticas (impuesto, plazo, costo, redondeo) siguen
        pudiendo crearse sobre un asiento publicado.
        """
        display_type = vals.get("display_type")
        if display_type in ("product", "line_section", "line_note"):
            return True
        return not display_type and bool(vals.get("product_id"))

    @api.model
    def _reject_commercial_lines_on_locked_moves(self, vals_list):
        if self.env.context.get("skip_readonly_check"):
            return
        move_ids = [
            vals["move_id"]
            for vals in vals_list
            if vals.get("move_id")
            and self._posted_catalog_vals_is_commercial_line(vals)
        ]
        if not move_ids:
            return
        locked = self.env["account.move"].browse(move_ids).filtered(
            lambda move: move.state != "draft"
        )
        if locked:
            locked[0]._raise_if_posted_catalog_locked()

    @api.model_create_multi
    def create(self, vals_list):
        self._reject_commercial_lines_on_locked_moves(vals_list)
        return super().create(vals_list)
