from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PbaSupplierBackorderProductWizard(models.TransientModel):
    _name = "pba.supplier.backorder.product.wizard"
    _description = "Crear producto desde backorder"

    import_line_id = fields.Many2one(
        comodel_name="pba.supplier.backorder.import.line",
        required=True,
        ondelete="cascade",
    )
    name = fields.Char(string="Nombre", required=True)
    default_code = fields.Char(string="Referencia interna", required=True)
    categ_id = fields.Many2one(
        comodel_name="product.category",
        string="Categoría",
        required=True,
        default=lambda self: self.env.ref(
            "product.product_category_all", raise_if_not_found=False
        ),
    )
    uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="UdM",
        required=True,
        default=lambda self: self.env.ref("uom.product_uom_unit").id,
    )
    purchase_ok = fields.Boolean(string="Se puede comprar", default=True)
    sale_ok = fields.Boolean(string="Se puede vender", default=True)
    list_price = fields.Float(string="Precio de venta", digits="Product Price")
    standard_price = fields.Float(string="Costo", digits="Product Price")
    company_id = fields.Many2one(
        related="import_line_id.wizard_id.company_id",
        readonly=True,
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        line = self.env["pba.supplier.backorder.import.line"].browse(
            self.env.context.get("default_import_line_id")
        )
        if line and line.exists():
            if "uom_id" in fields_list and not res.get("uom_id"):
                res["uom_id"] = line.uom_id.id or line.wizard_id._resolve_uom(
                    line.uom_name
                ).id
            if "standard_price" in fields_list and not res.get("standard_price"):
                res["standard_price"] = line.unit_price
        return res

    def action_back_to_import(self):
        self.ensure_one()
        return self.import_line_id.wizard_id.get_reopen_form_action()

    def action_open_from_template(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Importar de uno ya existente"),
            "res_model": "pba.supplier.backorder.product.from.template.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_import_line_id": self.import_line_id.id,
                "default_name": self.name,
                "default_default_code": self.default_code,
            },
        }

    def action_create_product(self):
        self.ensure_one()
        ProductTemplate = self.env["product.template"]
        vals = {
            "name": self.name,
            "default_code": self.default_code,
            "categ_id": self.categ_id.id,
            "uom_id": self.uom_id.id,
            "uom_po_id": self.uom_id.id,
            "purchase_ok": self.purchase_ok,
            "sale_ok": self.sale_ok,
            "list_price": self.list_price,
            "standard_price": self.standard_price,
            "type": "consu",
        }
        if "is_storable" in ProductTemplate._fields:
            vals["is_storable"] = True
        line = self.import_line_id
        tmpl = ProductTemplate.with_context(
            pba_backorder_import_line_id=line.id,
        ).create(vals)
        tmpl.pba_backorder_import_line_ref = line.id
        line.action_pba_assign_product(tmpl.product_variant_id)
        return line.wizard_id.get_reopen_form_action()
