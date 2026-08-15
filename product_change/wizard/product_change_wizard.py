from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero


class ProductChangeWizard(models.TransientModel):
    _name = "product.change.wizard"
    _description = "Change product type, tracking and unit of measure"

    product_tmpl_ids = fields.Many2many(
        comodel_name="product.template",
        relation="product_change_wizard_rel",
        column1="wizard_id",
        column2="product_tmpl_id",
        string="Products",
        readonly=True,
    )
    product_count = fields.Integer(compute="_compute_product_count")
    current_type = fields.Selection(
        selection=[
            ("consu", "Goods"),
            ("service", "Service"),
            ("combo", "Combo"),
        ],
        compute="_compute_current_values",
    )
    current_is_storable = fields.Boolean(compute="_compute_current_values")
    current_uom_id = fields.Many2one(
        comodel_name="uom.uom",
        compute="_compute_current_values",
    )
    change_type = fields.Boolean(string="Change Product Type")
    new_type = fields.Selection(
        selection=[
            ("consu", "Goods"),
            ("service", "Service"),
        ],
        string="New Type",
    )
    change_tracking = fields.Boolean(string="Change Inventory Tracking")
    new_tracking = fields.Selection(
        selection=[
            ("none", "No Tracking"),
            ("quantity", "Track by Quantity"),
        ],
        string="New Tracking",
    )
    change_uom = fields.Boolean(string="Change Unit of Measure")
    new_uom_id = fields.Many2one(comodel_name="uom.uom", string="New Unit of Measure")
    convert_uom_qty = fields.Boolean(
        string="Convert Quantities",
        help="When the new unit is in the same category, convert quantities "
        "and unit prices so document totals stay the same.",
    )
    same_uom_category = fields.Boolean(compute="_compute_same_uom_category")

    @api.depends("product_tmpl_ids")
    def _compute_product_count(self):
        for wizard in self:
            wizard.product_count = len(wizard.product_tmpl_ids)

    @api.depends("product_tmpl_ids")
    def _compute_current_values(self):
        for wizard in self:
            template = wizard.product_tmpl_ids[:1]
            wizard.current_type = template.type if template else False
            wizard.current_is_storable = bool(template.is_storable) if template else False
            wizard.current_uom_id = template.uom_id if template else False

    @api.depends("new_uom_id", "product_tmpl_ids")
    def _compute_same_uom_category(self):
        for wizard in self:
            templates = wizard.product_tmpl_ids
            new_uom = wizard.new_uom_id
            wizard.same_uom_category = bool(
                new_uom
                and templates
                and all(template.uom_id.category_id == new_uom.category_id for template in templates)
            )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        templates = self._get_templates_from_context()
        if templates:
            res["product_tmpl_ids"] = [(6, 0, templates.ids)]
            first = templates[0]
            res["new_type"] = "service" if first.type == "consu" else "consu"
            res["new_tracking"] = "none" if first.is_storable else "quantity"
            res["new_uom_id"] = first.uom_id.id
        return res

    @api.model
    def _get_templates_from_context(self):
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids", [])
        if not active_ids:
            return self.env["product.template"]
        if active_model == "product.template":
            return self.env["product.template"].browse(active_ids)
        if active_model == "product.product":
            return (
                self.env["product.product"].browse(active_ids).mapped("product_tmpl_id")
            )
        return self.env["product.template"]

    def action_apply(self):
        self.ensure_one()
        templates = self.product_tmpl_ids or self._get_templates_from_context()
        if not templates:
            raise UserError(_("Please select at least one product."))
        self._validate(templates)
        for template in templates:
            self._apply_to_template(template)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Product updated"),
                "message": _(
                    "%(count)s product(s) were updated. Sales, purchases and "
                    "invoices were kept. Incoming and outgoing stock was "
                    "rebuilt or generated when needed."
                )
                % {"count": len(templates)},
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def _validate(self, templates):
        if not (self.change_type or self.change_tracking or self.change_uom):
            raise UserError(_("Select at least one change: type, tracking or unit of measure."))
        if self.change_type and not self.new_type:
            raise UserError(_("Please choose the new product type."))
        if self.change_tracking and not self.new_tracking:
            raise UserError(_("Please choose the new inventory tracking."))
        if self.change_uom and not self.new_uom_id:
            raise UserError(_("Please choose the new unit of measure."))
        combos = templates.filtered(lambda template: template.type == "combo")
        if combos:
            raise UserError(
                _("Combo products cannot be converted:\n%s")
                % "\n".join(combos.mapped("display_name"))
            )
        if self.change_type and self.new_type == "service" and self.change_tracking:
            if self.new_tracking == "quantity":
                raise UserError(_("A service cannot track inventory by quantity."))

    def _apply_to_template(self, template):
        snapshots = self._snapshot_order_quantities(template)
        if self.change_uom and template.uom_id != self.new_uom_id:
            self._change_uom(template)
        if self.change_type and template.type != self.new_type:
            if self.new_type == "service":
                self._convert_to_service(template, snapshots)
            else:
                self._convert_to_goods(template, snapshots)
        target_storable = self._get_target_storable(template)
        if template.is_storable != target_storable:
            if target_storable:
                self._enable_quantity_tracking(template)
            else:
                self._disable_quantity_tracking(template)
        self._sync_order_qty_methods(template, snapshots)

    def _get_target_storable(self, template):
        if template.type == "service":
            return False
        if self.change_tracking:
            return self.new_tracking == "quantity"
        return template.is_storable

    def _snapshot_order_quantities(self, template):
        products = template.product_variant_ids
        sale_lines = self.env["sale.order.line"].search(
            [
                ("product_id", "in", products.ids),
                ("display_type", "=", False),
                ("state", "in", ["sale", "done"]),
            ]
        )
        purchase_lines = self.env["purchase.order.line"].search(
            [
                ("product_id", "in", products.ids),
                ("display_type", "=", False),
                ("state", "in", ["purchase", "done"]),
            ]
        )
        return {
            "sale": {line.id: line.qty_delivered for line in sale_lines},
            "purchase": {line.id: line.qty_received for line in purchase_lines},
        }

    def _convert_to_service(self, template, snapshots):
        template._product_change_unreserve()
        template._product_change_cancel_open_moves()
        template._product_change_archive_orderpoints()
        template._product_change_zero_quants()
        template.with_context(allow_product_change=True).write(
            {
                "type": "service",
                "is_storable": False,
                "tracking": "none",
            }
        )
        self._restore_manual_order_quantities(template, snapshots)

    def _convert_to_goods(self, template, snapshots):
        template.with_context(allow_product_change=True).write(
            {
                "type": "consu",
                "is_storable": False,
                "tracking": "none",
            }
        )
        self._generate_historical_stock(template, snapshots)
        self._launch_remaining_operations(template, snapshots)

    def _enable_quantity_tracking(self, template):
        template.with_context(allow_product_change=True).write(
            {
                "is_storable": True,
                "tracking": "none",
            }
        )
        template._rebuild_stock_quants_from_moves()

    def _disable_quantity_tracking(self, template):
        template._product_change_unreserve()
        template._product_change_archive_orderpoints()
        template._product_change_zero_quants()
        template.with_context(allow_product_change=True).write(
            {
                "is_storable": False,
                "tracking": "none",
            }
        )

    def _restore_manual_order_quantities(self, template, snapshots):
        sale_lines = self.env["sale.order.line"].browse(list(snapshots["sale"]))
        if sale_lines:
            sale_lines._compute_qty_delivered_method()
            for line in sale_lines:
                line.qty_delivered = snapshots["sale"][line.id]
        purchase_lines = self.env["purchase.order.line"].browse(list(snapshots["purchase"]))
        if purchase_lines:
            for line in purchase_lines:
                line.qty_received_manual = snapshots["purchase"][line.id]
            purchase_lines.invalidate_recordset(["qty_received_method", "qty_received"])
            purchase_lines._compute_qty_received_method()
            purchase_lines._compute_qty_received()

    def _sync_order_qty_methods(self, template, snapshots):
        if template.type == "service":
            self._restore_manual_order_quantities(template, snapshots)
            return
        sale_lines = self.env["sale.order.line"].browse(list(snapshots["sale"]))
        if sale_lines:
            sale_lines._compute_qty_delivered_method()
            sale_lines._compute_qty_delivered()
        purchase_lines = self.env["purchase.order.line"].browse(list(snapshots["purchase"]))
        if purchase_lines:
            purchase_lines.invalidate_recordset(["qty_received_method", "qty_received"])
            purchase_lines._compute_qty_received_method()
            purchase_lines._compute_qty_received()

    def _generate_historical_stock(self, template, snapshots):
        self._generate_stock_from_sale_lines(template, snapshots)
        self._generate_stock_from_purchase_lines(template, snapshots)
        self._generate_stock_from_orphan_invoices(template)

    def _generate_stock_from_sale_lines(self, template, snapshots):
        sale_lines = self.env["sale.order.line"].browse(list(snapshots["sale"]))
        for line in sale_lines:
            qty = snapshots["sale"][line.id]
            if float_is_zero(qty, precision_rounding=line.product_uom.rounding):
                qty = line.qty_invoiced
            if float_is_zero(qty, precision_rounding=line.product_uom.rounding):
                continue
            existing = line.move_ids.filtered(lambda move: move.state == "done")
            if existing:
                continue
            warehouse = line.order_id.warehouse_id or self._get_warehouse(line.company_id)
            partner = line.order_id.partner_shipping_id or line.order_id.partner_id
            self._create_done_stock_move(
                product=line.product_id,
                qty=qty,
                uom=line.product_uom,
                location=warehouse.lot_stock_id,
                location_dest=partner.property_stock_customer,
                picking_type=warehouse.out_type_id,
                partner=partner,
                origin=line.order_id.name,
                date=line.order_id.date_order,
                company=line.company_id,
                sale_line=line,
            )

    def _generate_stock_from_purchase_lines(self, template, snapshots):
        purchase_lines = self.env["purchase.order.line"].browse(list(snapshots["purchase"]))
        for line in purchase_lines:
            qty = snapshots["purchase"][line.id]
            if float_is_zero(qty, precision_rounding=line.product_uom.rounding):
                qty = line.qty_invoiced
            if float_is_zero(qty, precision_rounding=line.product_uom.rounding):
                continue
            existing = line.move_ids.filtered(lambda move: move.state == "done")
            if existing:
                continue
            warehouse = line.order_id.picking_type_id.warehouse_id or self._get_warehouse(
                line.company_id
            )
            partner = line.order_id.partner_id
            self._create_done_stock_move(
                product=line.product_id,
                qty=qty,
                uom=line.product_uom,
                location=partner.property_stock_supplier,
                location_dest=warehouse.lot_stock_id,
                picking_type=warehouse.in_type_id,
                partner=partner,
                origin=line.order_id.name,
                date=line.date_planned or line.order_id.date_order,
                company=line.company_id,
                purchase_line=line,
            )

    def _generate_stock_from_orphan_invoices(self, template):
        products = template.product_variant_ids
        invoice_lines = self.env["account.move.line"].search(
            [
                ("product_id", "in", products.ids),
                ("parent_state", "=", "posted"),
                ("display_type", "=", "product"),
                (
                    "move_id.move_type",
                    "in",
                    ("out_invoice", "out_refund", "in_invoice", "in_refund"),
                ),
                ("sale_line_ids", "=", False),
                ("purchase_line_id", "=", False),
            ]
        )
        for line in invoice_lines:
            qty = line.quantity
            if float_is_zero(qty, precision_rounding=line.product_uom_id.rounding):
                continue
            company = line.company_id
            warehouse = self._get_warehouse(company)
            partner = line.move_id.partner_id
            move_type = line.move_id.move_type
            if move_type in ("out_invoice", "in_refund"):
                location = warehouse.lot_stock_id
                location_dest = partner.property_stock_customer
                picking_type = warehouse.out_type_id
            else:
                location = partner.property_stock_supplier
                location_dest = warehouse.lot_stock_id
                picking_type = warehouse.in_type_id
            self._create_done_stock_move(
                product=line.product_id,
                qty=qty,
                uom=line.product_uom_id,
                location=location,
                location_dest=location_dest,
                picking_type=picking_type,
                partner=partner,
                origin=line.move_id.name,
                date=line.move_id.invoice_date or line.move_id.date,
                company=company,
            )

    def _launch_remaining_operations(self, template, snapshots):
        sale_lines = self.env["sale.order.line"].browse(list(snapshots["sale"]))
        sale_lines.filtered(
            lambda line: line.state == "sale" and not line.order_id.locked
        )._action_launch_stock_rule()
        purchase_orders = (
            self.env["purchase.order.line"]
            .browse(list(snapshots["purchase"]))
            .mapped("order_id")
            .filtered(lambda order: order.state in ("purchase", "done"))
        )
        if purchase_orders:
            purchase_orders._create_picking()

    def _create_done_stock_move(
        self,
        product,
        qty,
        uom,
        location,
        location_dest,
        picking_type,
        partner,
        origin,
        date,
        company,
        sale_line=False,
        purchase_line=False,
    ):
        if float_is_zero(qty, precision_rounding=uom.rounding):
            return self.env["stock.move"]
        if sale_line and sale_line.order_id and not sale_line.order_id.procurement_group_id:
            group = self.env["procurement.group"].create(
                sale_line._prepare_procurement_group_vals()
            )
            sale_line.order_id.procurement_group_id = group
        picking = self.env["stock.picking"].create(
            {
                "picking_type_id": picking_type.id,
                "location_id": location.id,
                "location_dest_id": location_dest.id,
                "partner_id": partner.id,
                "origin": origin,
                "scheduled_date": date,
                "company_id": company.id,
            }
        )
        values = {
            "name": product.display_name,
            "product_id": product.id,
            "product_uom": uom.id,
            "product_uom_qty": qty,
            "location_id": location.id,
            "location_dest_id": location_dest.id,
            "picking_id": picking.id,
            "picking_type_id": picking_type.id,
            "origin": origin,
            "company_id": company.id,
            "date": date,
            "partner_id": partner.id,
        }
        if sale_line:
            values["sale_line_id"] = sale_line.id
            values["group_id"] = sale_line.order_id.procurement_group_id.id
        if purchase_line:
            values["purchase_line_id"] = purchase_line.id
            values["group_id"] = purchase_line.order_id.group_id.id
            values["price_unit"] = purchase_line._get_stock_move_price_unit()
        move = self.env["stock.move"].create(values)
        move._action_confirm()
        move.quantity = qty
        move.picked = True
        move._action_done()
        if date:
            move.write({"date": date})
            move.move_line_ids.write({"date": date})
        return move

    def _get_warehouse(self, company):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", company.id)], limit=1
        )
        if not warehouse:
            raise UserError(
                _("No warehouse found for company %s.") % company.display_name
            )
        return warehouse

    def _change_uom(self, template):
        old_uom = template.uom_id
        new_uom = self.new_uom_id
        convert = bool(
            self.convert_uom_qty and old_uom.category_id == new_uom.category_id
        )
        products = template.product_variant_ids
        self._update_related_uoms(products, new_uom, convert)
        vals = {"uom_id": new_uom.id}
        if template.uom_po_id.category_id != new_uom.category_id:
            vals["uom_po_id"] = new_uom.id
        template.with_context(allow_product_change=True).write(vals)

    def _update_related_uoms(self, products, new_uom, convert):
        self._update_sale_line_uoms(products, new_uom, convert)
        self._update_purchase_line_uoms(products, new_uom, convert)
        self._update_invoice_line_uoms(products, new_uom, convert)
        self._update_stock_uoms(products, new_uom, convert)

    def _update_sale_line_uoms(self, products, new_uom, convert):
        lines = self.env["sale.order.line"].search(
            [("product_id", "in", products.ids), ("display_type", "=", False)]
        )
        for line in lines:
            values = {"product_uom": new_uom.id}
            if convert and line.product_uom.category_id == new_uom.category_id:
                values["product_uom_qty"] = line.product_uom._compute_quantity(
                    line.product_uom_qty, new_uom, rounding_method="HALF-UP"
                )
                values["price_unit"] = line.product_uom._compute_price(
                    line.price_unit, new_uom
                )
                if line.qty_delivered_method == "manual":
                    values["qty_delivered"] = line.product_uom._compute_quantity(
                        line.qty_delivered, new_uom, rounding_method="HALF-UP"
                    )
            self._sql_write("sale.order.line", line.id, values)

    def _update_purchase_line_uoms(self, products, new_uom, convert):
        lines = self.env["purchase.order.line"].search(
            [("product_id", "in", products.ids), ("display_type", "=", False)]
        )
        for line in lines:
            values = {"product_uom": new_uom.id}
            if convert and line.product_uom.category_id == new_uom.category_id:
                values["product_qty"] = line.product_uom._compute_quantity(
                    line.product_qty, new_uom, rounding_method="HALF-UP"
                )
                values["price_unit"] = line.product_uom._compute_price(
                    line.price_unit, new_uom
                )
                values["qty_received_manual"] = line.product_uom._compute_quantity(
                    line.qty_received_manual, new_uom, rounding_method="HALF-UP"
                )
            self._sql_write("purchase.order.line", line.id, values)

    def _update_invoice_line_uoms(self, products, new_uom, convert):
        lines = self.env["account.move.line"].search(
            [
                ("product_id", "in", products.ids),
                ("display_type", "=", "product"),
            ]
        )
        for line in lines:
            values = {"product_uom_id": new_uom.id}
            if (
                convert
                and line.parent_state != "posted"
                and line.product_uom_id.category_id == new_uom.category_id
            ):
                values["quantity"] = line.product_uom_id._compute_quantity(
                    line.quantity, new_uom, rounding_method="HALF-UP"
                )
                values["price_unit"] = line.product_uom_id._compute_price(
                    line.price_unit, new_uom
                )
            self._sql_write("account.move.line", line.id, values)

    def _update_stock_uoms(self, products, new_uom, convert):
        moves = self.env["stock.move"].search([("product_id", "in", products.ids)])
        for move in moves:
            values = {"product_uom": new_uom.id}
            if convert and move.product_uom.category_id == new_uom.category_id:
                values["product_uom_qty"] = move.product_uom._compute_quantity(
                    move.product_uom_qty, new_uom, rounding_method="HALF-UP"
                )
                values["quantity"] = move.product_uom._compute_quantity(
                    move.quantity, new_uom, rounding_method="HALF-UP"
                )
            self._sql_write("stock.move", move.id, values)
        move_lines = self.env["stock.move.line"].search(
            [("product_id", "in", products.ids)]
        )
        for move_line in move_lines:
            values = {"product_uom_id": new_uom.id}
            if convert and move_line.product_uom_id.category_id == new_uom.category_id:
                values["quantity"] = move_line.product_uom_id._compute_quantity(
                    move_line.quantity, new_uom, rounding_method="HALF-UP"
                )
            self._sql_write("stock.move.line", move_line.id, values)

    def _sql_write(self, model_name, record_id, values):
        if not values:
            return
        model = self.env[model_name]
        assignments = []
        params = []
        for field_name, value in values.items():
            assignments.append("%s = %%s" % field_name)
            params.append(value)
        params.append(record_id)
        self.env.cr.execute(
            "UPDATE %s SET %s WHERE id = %%s"
            % (model._table, ", ".join(assignments)),
            params,
        )
        model.browse(record_id).invalidate_recordset(list(values))
