from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    auto_generated = fields.Boolean(
        string="Auto Generated Sales Order",
        copy=False,
    )
    auto_purchase_order_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Source Purchase Order",
        readonly=True,
        copy=False,
        index="btree_not_null",
    )
    ic_purchase_order_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Inter-Company Purchase Order",
        readonly=True,
        copy=False,
        index="btree_not_null",
    )
    ic_purchase_order_display = fields.Char(
        string="Inter-Company Purchase Order",
        compute="_compute_ic_purchase_order_display",
    )
    is_intercompany_customer = fields.Boolean(
        compute="_compute_is_intercompany_customer",
    )
    ic_show_sync_button = fields.Boolean(
        compute="_compute_ic_show_sync_button",
    )

    @api.depends("ic_purchase_order_id", "auto_purchase_order_id")
    def _compute_ic_purchase_order_display(self):
        for order in self:
            purchase_order = (
                order.sudo().ic_purchase_order_id or order.sudo().auto_purchase_order_id
            )
            if purchase_order:
                order.ic_purchase_order_display = "%s (%s)" % (
                    purchase_order.name,
                    purchase_order.company_id.name,
                )
            else:
                order.ic_purchase_order_display = False

    @api.depends("partner_id")
    def _compute_is_intercompany_customer(self):
        Company = self.env["res.company"]
        for order in self:
            company = (
                Company._find_company_from_partner(order.partner_id.id)
                if order.partner_id
                else Company.browse()
            )
            order.is_intercompany_customer = bool(company and company != order.company_id)

    @api.depends(
        "partner_id",
        "auto_generated",
        "ic_purchase_order_id",
        "order_line",
        "company_id",
    )
    def _compute_ic_show_sync_button(self):
        for order in self:
            order.ic_show_sync_button = order._ic_can_manual_sync()

    def _ic_can_manual_sync(self):
        self.ensure_one()
        order = self.sudo()
        if (
            not order.id
            or order.auto_generated
            or order.ic_purchase_order_id
            or not order.order_line
        ):
            return False
        company = self.env["res.company"]._find_company_from_partner(order.partner_id.id)
        if not company or company == order.company_id or not company.ic_po_from_so:
            return False
        existing = (
            self.env["purchase.order"]
            .sudo()
            .search([("auto_sale_order_id", "=", order.id)], limit=1)
        )
        return not bool(existing)

    def action_ic_sync_purchase_order(self):
        self.ensure_one()
        if not self._ic_can_manual_sync():
            raise UserError(
                _("This sales order is already synchronized or cannot be synced.")
            )
        force_draft = self.state in ("draft", "sent")
        purchase_order = self._ic_try_create_purchase_order(force_draft=force_draft)
        if not purchase_order:
            raise UserError(_("Could not create the inter-company purchase order."))
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Inter-Company Sync"),
                "message": _(
                    "Purchase order %(name)s created in company %(company)s.",
                    name=purchase_order.sudo().name,
                    company=purchase_order.sudo().company_id.name,
                ),
                "type": "success",
                "sticky": False,
            },
        }

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get("skip_ic_so_write_sync"):
            return res
        sync_keys = {
            "partner_id",
            "order_line",
            "date_order",
            "currency_id",
            "commitment_date",
        }
        if sync_keys.intersection(vals):
            for order in self.filtered(lambda so: so.state in ("draft", "sent")):
                order._ic_sync_counterpart_purchase()
        return res

    def _action_confirm(self):
        res = super()._action_confirm()
        for order in self:
            order._ic_try_create_purchase_order(force_draft=False)
        return res

    def _ic_get_linked_purchase_order(self):
        self.ensure_one()
        order = self.sudo()
        purchase_order = order.ic_purchase_order_id
        if not purchase_order:
            purchase_order = order.auto_purchase_order_id
        if not purchase_order:
            purchase_order = (
                self.env["purchase.order"]
                .sudo()
                .search([("auto_sale_order_id", "=", self.id)], limit=1)
            )
            if purchase_order and not order.ic_purchase_order_id:
                order.with_context(skip_ic_so_write_sync=True).write(
                    {"ic_purchase_order_id": purchase_order.id}
                )
        return purchase_order

    def _ic_sync_counterpart_purchase(self):
        self.ensure_one()
        if self.env.context.get("skip_ic_so_write_sync") or not self.order_line:
            return self.env["purchase.order"]
        if self.state not in ("draft", "sent"):
            return self.env["purchase.order"]
        purchase_order = self._ic_get_linked_purchase_order()
        if not purchase_order:
            return self.env["purchase.order"]
        purchase_order = purchase_order.sudo()
        if purchase_order.state not in ("draft", "sent"):
            return purchase_order
        company = purchase_order.company_id
        self._ic_update_purchase_order_lines(purchase_order, company)
        return purchase_order

    def _ic_update_purchase_order_lines(self, purchase_order, company):
        self.ensure_one()
        purchase_order = purchase_order.sudo()
        commands = [(5, 0, 0)]
        for line in self.order_line.sudo():
            commands.append(
                (0, 0, self._prepare_ic_purchase_order_line_data(line, self.date_order, company))
            )
        purchase_order.with_company(company).with_context(
            allowed_company_ids=company.ids,
            skip_ic_po_write_sync=True,
            skip_ic_po_create_sync=True,
            skip_ic_po_price_compute=True,
        ).write(
            {
                "partner_ref": self.name,
                "date_order": self.date_order,
                "currency_id": self.currency_id.id,
                "order_line": commands,
            }
        )
        so_lines = self.order_line.sudo().filtered(lambda line: not line.display_type)
        po_lines = purchase_order.order_line.filtered(lambda line: not line.display_type)
        for so_line, po_line in zip(so_lines, po_lines):
            line_vals = self._prepare_ic_purchase_order_line_data(
                so_line, self.date_order, company
            )
            po_line.with_company(company).with_context(
                allowed_company_ids=company.ids,
                skip_ic_po_write_sync=True,
                skip_ic_po_price_compute=True,
                skip_ic_so_write_sync=True,
            ).write(
                {
                    "price_unit": line_vals["price_unit"],
                    "discount": line_vals.get("discount", 0.0),
                    "product_qty": line_vals["product_qty"],
                }
            )

    def _ic_try_create_purchase_order(self, force_draft=False):
        self.ensure_one()
        order = self.sudo()
        if not order.company_id or order.auto_generated:
            return self.env["purchase.order"]

        purchase_order = self._ic_get_linked_purchase_order()
        if purchase_order:
            purchase_order = purchase_order.sudo()
            if not force_draft and purchase_order.state in ("draft", "sent"):
                self._ic_update_purchase_order_lines(
                    purchase_order, purchase_order.company_id
                )
                return self._ic_confirm_linked_purchase_order(
                    purchase_order, purchase_order.company_id
                )
            return purchase_order

        company = self.env["res.company"]._find_company_from_partner(order.partner_id.id)
        if not company or company == order.company_id:
            return self.env["purchase.order"]
        if not company.ic_po_from_so:
            self.message_post(
                body=_(
                    "Inter-company purchase order was not created because company %(company)s "
                    "has 'Generate Purchase Orders from Sales' disabled.",
                    company=company.name,
                )
            )
            return self.env["purchase.order"]
        return self.sudo()._ic_create_purchase_order(company, force_draft=force_draft)

    def _ic_confirm_linked_purchase_order(self, purchase_order, company):
        purchase_order = purchase_order.sudo()
        if purchase_order.state not in ("draft", "sent"):
            return purchase_order
        if company.ic_po_state != "confirmed":
            return purchase_order
        ic_user = company._ic_ensure_user(["purchase", "stock"])
        purchase_order.with_user(ic_user).with_company(company).with_context(
            allowed_company_ids=company.ids
        ).button_confirm()
        return purchase_order

    def _ic_create_purchase_order(self, company, force_draft=False):
        self.ensure_one()
        confirm_purchase = (not force_draft) and company.ic_po_state == "confirmed"
        rights = ["purchase"]
        if confirm_purchase:
            rights.append("stock")
        ic_user = company._ic_ensure_user(rights)
        self._ic_check_shared_products(company)
        company_partner = self.company_id.partner_id.sudo().with_company(company)
        po_vals = self.sudo()._prepare_ic_purchase_order_data(company, company_partner)
        for line in self.order_line.sudo():
            po_vals["order_line"].append(
                (0, 0, self._prepare_ic_purchase_order_line_data(line, self.date_order, company))
            )
        purchase_order = (
            self.env["purchase.order"]
            .with_user(ic_user)
            .with_company(company)
            .with_context(allowed_company_ids=company.ids, skip_ic_po_create_sync=True)
            .sudo()
            .create(po_vals)
        )
        purchase_order.sudo().message_post(
            body=_(
                "Automatically generated from %(origin)s of company %(company)s.",
                origin=self.name,
                company=self.company_id.name,
            )
        )
        vals = {"ic_purchase_order_id": purchase_order.id}
        if not self.client_order_ref:
            vals["client_order_ref"] = purchase_order.name
        self.sudo().with_company(self.company_id).with_context(
            skip_ic_so_write_sync=True
        ).write(vals)
        if confirm_purchase:
            purchase_order.with_user(ic_user).with_company(company).with_context(
                allowed_company_ids=company.ids
            ).sudo().button_confirm()
        return purchase_order

    def _ic_check_shared_products(self, company):
        if not company.ic_block_unshared_product:
            return
        products = self.order_line.mapped("product_id").filtered(
            lambda product: product.company_id and product.company_id != company
        )
        if products:
            raise UserError(
                _(
                    "The following products are not shared with company %(company)s: %(products)s",
                    company=company.name,
                    products=", ".join(products.mapped("display_name")),
                )
            )

    def _prepare_ic_purchase_order_data(self, company, company_partner):
        self.ensure_one()
        warehouse = company._ic_get_warehouse()
        if not warehouse:
            raise UserError(
                _(
                    "Configure a warehouse for company %(name)s in Inter-Company settings.",
                    name=company.name,
                )
            )
        picking_type = company.ic_receipt_type_id
        if not picking_type:
            picking_type = self.env["stock.picking.type"].sudo().search(
                [("code", "=", "incoming"), ("warehouse_id", "=", warehouse.id)],
                limit=1,
            )
        if not picking_type:
            picking_type = (
                self.env["purchase.order"]
                .sudo()
                .with_company(company)
                ._default_picking_type()
            )
        return {
            "name": self.env["ir.sequence"].sudo().next_by_code("purchase.order") or "/",
            "origin": self.name,
            "partner_id": company_partner.id,
            "date_order": self.date_order,
            "company_id": company.id,
            "fiscal_position_id": self.env["account.fiscal.position"]
            .sudo()
            .with_company(company)
            ._get_fiscal_position(company_partner)
            .id,
            "payment_term_id": company_partner.property_supplier_payment_term_id.id,
            "auto_generated": True,
            "auto_sale_order_id": self.id,
            "partner_ref": self.name,
            "currency_id": self.currency_id.id,
            "picking_type_id": picking_type.id,
            "order_line": [],
        }

    @api.model
    def _prepare_ic_purchase_order_line_data(self, so_line, date_order, company):
        price = so_line.price_unit or 0.0
        quantity = so_line.product_uom_qty
        uom = so_line.product_uom
        if so_line.product_id:
            quantity = so_line.product_uom._compute_quantity(
                so_line.product_uom_qty, so_line.product_id.uom_po_id
            )
            price = so_line.product_uom._compute_price(price, so_line.product_id.uom_po_id)
            uom = so_line.product_id.uom_po_id
        return {
            "name": so_line.name,
            "product_qty": quantity,
            "product_id": so_line.product_id.id if so_line.product_id else False,
            "product_uom": uom.id if uom else False,
            "price_unit": price or 0.0,
            "discount": so_line.discount or 0.0,
            "company_id": company.id,
            "date_planned": so_line.order_id.commitment_date
            or so_line.order_id.expected_date
            or date_order,
            "display_type": so_line.display_type,
        }
