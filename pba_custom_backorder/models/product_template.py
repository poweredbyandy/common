from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    pba_backorder_import_line_ref = fields.Integer(
        string="Línea importación backorder (ref)",
        copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        line_ref = self.env.context.get("pba_backorder_import_line_id")
        if line_ref:
            for vals in vals_list:
                vals.setdefault("pba_backorder_import_line_ref", line_ref)
        return super().create(vals_list)

    def action_pba_back_to_import(self):
        self.ensure_one()
        line = self._pba_get_backorder_import_line()
        return line.wizard_id.get_reopen_form_action()

    def action_pba_backorder_save_and_return(self):
        self.ensure_one()
        line = self._pba_get_backorder_import_line()
        line.action_pba_assign_product(self.product_variant_id)
        return line.wizard_id.get_reopen_form_action()

    def action_pba_open_from_template(self):
        self.ensure_one()
        line = self._pba_get_backorder_import_line()
        return {
            "type": "ir.actions.act_window",
            "name": _("Importar de uno ya existente"),
            "res_model": "pba.supplier.backorder.product.from.template.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_import_line_id": line.id,
            },
        }

    def _pba_get_backorder_import_line(self, raise_if_missing=True):
        self.ensure_one()
        line_id = (
            self.env.context.get("pba_backorder_import_line_id")
            or self.pba_backorder_import_line_ref
        )
        if not line_id:
            if raise_if_missing:
                raise UserError(
                    _("No se encontró la línea de importación del backorder.")
                )
            return self.env["pba.supplier.backorder.import.line"]
        line = self.env["pba.supplier.backorder.import.line"].browse(line_id).exists()
        if not line and raise_if_missing:
            raise UserError(
                _("La línea de importación del backorder ya no está disponible.")
            )
        return line
