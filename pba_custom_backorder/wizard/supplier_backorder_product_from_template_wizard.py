from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PbaSupplierBackorderProductFromTemplateWizard(models.TransientModel):
    _name = "pba.supplier.backorder.product.from.template.wizard"
    _inherit = "pba.backorder.product.match.mixin"
    _description = "Duplicar producto plantilla para backorder"

    import_line_id = fields.Many2one(
        comodel_name="pba.supplier.backorder.import.line",
        required=True,
        ondelete="cascade",
    )
    template_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Producto plantilla",
        domain=[("active", "=", True)],
    )
    name = fields.Char(
        string="Nombre",
        readonly=True,
        help="Se conserva el nombre del producto plantilla.",
    )
    product_brand_id = fields.Many2one(
        comodel_name="product.brand",
        string="Marca",
    )
    internal_code = fields.Char(
        string="Código interno",
        help="Nº parte / código del archivo Excel.",
    )
    default_code = fields.Char(
        string="Referencia",
        help="Referencia interna; por defecto la del producto plantilla.",
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        line = self.env["pba.supplier.backorder.import.line"].browse(
            self.env.context.get("default_import_line_id")
        )
        if not line.exists():
            return res
        wizard = line.wizard_id
        if fields_list is None or "import_line_id" in fields_list:
            res.setdefault("import_line_id", line.id)
        if fields_list is None or "internal_code" in fields_list:
            res.setdefault("internal_code", wizard._line_excel_internal_code(line))
        if fields_list is None or "product_brand_id" in fields_list:
            brand_id = self.env.context.get("default_product_brand_id")
            if brand_id:
                res.setdefault("product_brand_id", brand_id)
            else:
                brand = wizard._resolve_brand_from_factory(line.factory)
                if brand:
                    res.setdefault("product_brand_id", brand.id)
        return res

    @api.onchange("template_product_id")
    def _onchange_template_product_id(self):
        if not self.template_product_id:
            return
        tmpl = self.template_product_id.product_tmpl_id
        line = self.import_line_id
        wizard = line.wizard_id
        self.name = tmpl.name
        self.default_code = tmpl.default_code or ""
        if not self.internal_code and line:
            self.internal_code = wizard._line_excel_internal_code(line)
        if line and line.factory:
            brand = wizard._resolve_brand_from_factory(line.factory)
            if brand:
                self.product_brand_id = brand
        elif tmpl.product_brand_id and not self.product_brand_id:
            self.product_brand_id = tmpl.product_brand_id

    def _duplicate_vals(self):
        self.ensure_one()
        source_tmpl = self.template_product_id.product_tmpl_id
        line = self.import_line_id
        wizard = line.wizard_id
        internal_code = (
            self.internal_code or wizard._line_excel_internal_code(line)
        )
        vals = {
            "name": source_tmpl.name,
            "default_code": self.default_code or source_tmpl.default_code,
            "internal_code": internal_code,
        }
        brand = self.product_brand_id
        if not brand and line.factory:
            brand = wizard._resolve_brand_from_factory(line.factory)
        if not brand:
            brand = source_tmpl.product_brand_id
        if brand:
            vals["product_brand_id"] = brand.id
        return vals

    def action_back_to_import(self):
        self.ensure_one()
        line = self.import_line_id
        if not line:
            raise UserError(_("No se encontró la línea de importación."))
        wizard = line.wizard_id
        self.unlink()
        return wizard.get_reopen_form_action()

    def action_duplicate_from_template(self):
        self.ensure_one()
        if not self.template_product_id:
            raise UserError(_("Seleccione un producto plantilla."))
        if not self.internal_code:
            raise UserError(_("Indique el código interno (nº parte del archivo)."))
        source_tmpl = self.template_product_id.product_tmpl_id
        line = self.import_line_id
        new_tmpl = source_tmpl.copy(default=self._duplicate_vals())
        if line.unit_price and not new_tmpl.standard_price:
            new_tmpl.standard_price = line.unit_price
        new_tmpl.write({"pba_backorder_import_line_ref": line.id})
        line.action_pba_assign_product(new_tmpl.product_variant_id)
        view = self.env.ref(
            "pba_custom_backorder.product_template_backorder_import_form_view",
            raise_if_not_found=False,
        )
        views = [(view.id, "form")] if view else [(False, "form")]
        return {
            "type": "ir.actions.act_window",
            "name": _("Producto"),
            "res_model": "product.template",
            "res_id": new_tmpl.id,
            "view_mode": "form",
            "views": views,
            "target": "new",
            "context": {
                "pba_backorder_import_line_id": line.id,
                "pba_from_backorder_import": True,
            },
        }
