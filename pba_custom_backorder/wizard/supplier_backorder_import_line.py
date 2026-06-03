from odoo import _, api, fields, models


class PbaSupplierBackorderImportLine(models.TransientModel):
    _name = "pba.supplier.backorder.import.line"
    _description = "Línea de importación de backorder de proveedor"
    _order = "sequence, id"

    wizard_id = fields.Many2one(
        comodel_name="pba.supplier.backorder.import.wizard",
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(default=10)
    internal_code = fields.Char(string="Nº parte / código interno", required=True)
    product_ref = fields.Char(string="Referencia (archivo)")
    description = fields.Char(string="Descripción")
    supplier_name = fields.Char(string="Proveedor (archivo)")
    factory = fields.Char(string="Fábrica")
    order_ref = fields.Char(string="Nº pedido")
    confirmation = fields.Char(string="Confirmación")
    quantity = fields.Float(string="Cantidad", digits="Product Unit of Measure")
    uom_name = fields.Char(string="Unidad (archivo)")
    unit_price = fields.Float(string="Precio unitario", digits="Product Price")
    line_total = fields.Float(string="Total línea", digits="Product Price")
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Producto",
    )
    product_match = fields.Selection(
        selection=[
            ("matched", "Encontrado"),
            ("missing", "Sin producto"),
            ("skipped", "Omitir"),
            ("created", "Creado"),
        ],
        string="Estado producto",
        default="missing",
        required=True,
    )
    uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="UdM",
    )
    company_id = fields.Many2one(related="wizard_id.company_id")

    @api.onchange("product_id")
    def _onchange_product_id(self):
        for line in self:
            if line.product_id:
                line.product_match = "matched"
                if not line.uom_id:
                    line.uom_id = line.product_id.uom_po_id or line.product_id.uom_id

    def action_pba_assign_product(self, product):
        self.ensure_one()
        if not product:
            return
        uom = self.uom_id or product.uom_po_id or product.uom_id
        self.write(
            {
                "product_id": product.id,
                "uom_id": uom.id if uom else False,
                "product_match": "created",
            }
        )

    def action_open_create_product(self):
        self.ensure_one()
        wizard = self.wizard_id
        uom = self.uom_id or wizard._resolve_uom(self.uom_name)
        view = self.env.ref(
            "pba_custom_backorder.product_template_backorder_import_form_view",
            raise_if_not_found=False,
        )
        views = [(view.id, "form")] if view else [(False, "form")]
        brand = wizard._resolve_brand_from_factory(self.factory)
        ctx = {
            "default_name": self.description or self.internal_code,
            "default_default_code": self.product_ref or "",
            "default_internal_code": wizard._line_excel_internal_code(self),
            "default_standard_price": self.unit_price,
            "default_uom_id": uom.id,
            "default_uom_po_id": uom.id,
            "default_purchase_ok": True,
            "default_sale_ok": True,
            "default_type": "consu",
            "pba_backorder_import_line_id": self.id,
            "pba_from_backorder_import": True,
        }
        ProductTemplate = self.env["product.template"]
        if "is_storable" in ProductTemplate._fields:
            ctx["default_is_storable"] = True
        if brand:
            ctx["default_product_brand_id"] = brand.id
        return {
            "type": "ir.actions.act_window",
            "name": _("Crear producto"),
            "res_model": "product.template",
            "view_mode": "form",
            "views": views,
            "target": "new",
            "context": ctx,
        }

    def action_open_from_template(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Importar de uno ya existente"),
            "res_model": "pba.supplier.backorder.product.from.template.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_import_line_id": self.id,
            },
        }

    def action_skip_line(self):
        self.ensure_one()
        self.write({"product_match": "skipped", "product_id": False})
        return self.wizard_id.get_reopen_form_action()
