from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    auto_generated = fields.Boolean(
        string="Auto Generated Purchase Order",
        copy=False,
    )
    auto_sale_order_id = fields.Many2one(
        comodel_name="sale.order",
        string="Source Sales Order",
        readonly=True,
        copy=False,
        index="btree_not_null",
    )
    ic_sale_order_id = fields.Many2one(
        comodel_name="sale.order",
        string="Inter-Company Sale Order",
        readonly=True,
        copy=False,
        index="btree_not_null",
    )
    is_intercompany_vendor = fields.Boolean(
        compute="_compute_is_intercompany_vendor",
    )
    ic_show_sync_button = fields.Boolean(
        compute="_compute_ic_show_sync_button",
    )

    @api.depends("partner_id")
    def _compute_is_intercompany_vendor(self):
        Company = self.env["res.company"]
        for order in self:
            order.is_intercompany_vendor = bool(
                order.partner_id and Company._find_company_from_partner(order.partner_id.id)
            )

    @api.depends(
        "partner_id",
        "auto_generated",
        "ic_sale_order_id",
        "order_line",
        "company_id",
    )
    def _compute_ic_show_sync_button(self):
        for order in self:
            order.ic_show_sync_button = order._ic_can_manual_sync()

    def _ic_can_manual_sync(self):
        self.ensure_one()
        if (
            not self.id
            or self.auto_generated
            or self.ic_sale_order_id
            or not self.order_line
        ):
            return False
        vendor_company = self._ic_get_vendor_company()
        if not vendor_company or not vendor_company.ic_so_from_po:
            return False
        existing = (
            self.env["sale.order"]
            .sudo()
            .search([("auto_purchase_order_id", "=", self.id)], limit=1)
        )
        return not bool(existing)

    def action_ic_sync_sale_order(self):
        self.ensure_one()
        if not self._ic_can_manual_sync():
            raise UserError(
                _("This purchase order is already synchronized or cannot be synced.")
            )
        force_draft = self.state in ("draft", "sent")
        sale_order = self._ic_sync_counterpart_sale(force_draft=force_draft)
        if not sale_order:
            raise UserError(_("Could not create the inter-company sales order."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Inter-Company Sale Order"),
            "res_model": "sale.order",
            "view_mode": "form",
            "res_id": sale_order.id,
            "target": "current",
        }

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        if self.env.context.get("skip_ic_po_create_sync"):
            return orders
        for order in orders.filtered(
            lambda po: po.state in ("draft", "sent") and not po.auto_generated
        ):
            order._ic_sync_counterpart_sale(force_draft=True)
        return orders

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get("skip_ic_po_write_sync"):
            return res
        sync_keys = {"partner_id", "order_line", "dest_address_id", "date_planned", "currency_id"}
        if sync_keys.intersection(vals):
            for order in self.filtered(lambda po: po.state in ("draft", "sent") and not po.auto_generated):
                order._ic_sync_counterpart_sale(force_draft=True)
        return res

    def button_approve(self, force=False):
        self._ic_check_confirm_allowed()
        to_approve = self.filtered(lambda order: order._approval_allowed())
        res = super().button_approve(force=force)
        for order in to_approve:
            if order.state not in ("purchase", "done"):
                continue
            order._ic_sync_counterpart_sale(force_draft=False)
        return res

    def button_confirm(self):
        self._ic_check_confirm_allowed()
        res = super().button_confirm()
        for order in self:
            if order.state not in ("purchase", "done"):
                continue
            order._ic_sync_counterpart_sale(force_draft=False)
        return res

    def _ic_get_vendor_company(self):
        self.ensure_one()
        if not self.partner_id:
            return self.env["res.company"]
        company = self.env["res.company"]._find_company_from_partner(self.partner_id.id)
        if company and company != self.company_id:
            return company
        return self.env["res.company"]

    def _ic_check_confirm_allowed(self):
        for order in self:
            if order.auto_generated:
                continue
            vendor_company = order._ic_get_vendor_company()
            if not vendor_company:
                continue
            if not order.company_id.ic_allow_confirm_ic_purchase:
                raise UserError(
                    _(
                        "Inter-company purchase orders cannot be confirmed for company %(company)s. "
                        "Enable 'Allow confirming inter-company purchases' in Sale/Purchase Sync settings.",
                        company=order.company_id.name,
                    )
                )

    def _ic_sync_counterpart_sale(self, force_draft=True):
        self.ensure_one()
        if self.auto_generated or not self.order_line:
            return self.env["sale.order"]
        vendor_company = self._ic_get_vendor_company()
        if not vendor_company:
            return self.env["sale.order"]
        if not vendor_company.ic_so_from_po:
            return self.env["sale.order"]

        sale_order = self.ic_sale_order_id
        if not sale_order:
            sale_order = (
                self.env["sale.order"]
                .sudo()
                .search([("auto_purchase_order_id", "=", self.id)], limit=1)
            )
            if sale_order:
                self.sudo().write({"ic_sale_order_id": sale_order.id})

        if sale_order:
            if force_draft or self.state in ("draft", "sent"):
                if sale_order.state in ("draft", "sent"):
                    self._ic_update_sale_order_lines(sale_order, vendor_company)
                return sale_order
            return self._ic_confirm_linked_sale_order(sale_order, vendor_company)

        return self.sudo()._ic_create_sale_order(vendor_company, force_draft=force_draft)

    def _ic_update_sale_order_lines(self, sale_order, company):
        self.ensure_one()
        commands = [(5, 0, 0)]
        for line in self.order_line.sudo():
            commands.append((0, 0, self._prepare_ic_sale_order_line_data(line, company)))
        sale_order.with_context(skip_ic_so_write_sync=True).sudo().write(
            {
                "client_order_ref": self.name,
                "date_order": self.date_order,
                "commitment_date": self.date_planned,
                "order_line": commands,
            }
        )

    def _ic_confirm_linked_sale_order(self, sale_order, company):
        self.ensure_one()
        if sale_order.state not in ("draft", "sent"):
            return sale_order
        if company.ic_so_state != "confirmed":
            return sale_order
        ic_user = company._ic_ensure_user(["sale", "stock"])
        sale_order.with_user(ic_user).with_company(company).with_context(
            allowed_company_ids=company.ids
        ).sudo().action_confirm()
        return sale_order

    def _ic_create_sale_order(self, company, force_draft=True):
        self.ensure_one()
        confirm_sale = (not force_draft) and company.ic_so_state == "confirmed"
        rights = ["sale"]
        if confirm_sale:
            rights.append("stock")
        ic_user = company._ic_ensure_user(rights)
        self._ic_check_shared_products(company)
        company_partner = self.company_id.partner_id.sudo().with_company(company)
        sale_order_data = self.sudo()._prepare_ic_sale_order_data(
            self.name,
            company_partner,
            company,
            self.dest_address_id.id or False,
        )
        for line in self.order_line.sudo():
            sale_order_data["order_line"].append(
                (0, 0, self._prepare_ic_sale_order_line_data(line, company))
            )
        sale_order = (
            self.env["sale.order"]
            .with_user(ic_user)
            .with_company(company)
            .with_context(allowed_company_ids=company.ids)
            .sudo()
            .create(sale_order_data)
        )
        sale_order.sudo().message_post(
            body=_(
                "Automatically generated from %(origin)s of company %(company)s.",
                origin=self.name,
                company=self.company_id.name,
            )
        )
        vals = {"ic_sale_order_id": sale_order.id}
        if not self.partner_ref:
            vals["partner_ref"] = sale_order.name
        self.sudo().with_company(self.company_id).write(vals)
        if confirm_sale:
            sale_order.with_user(ic_user).with_company(company).with_context(
                allowed_company_ids=company.ids
            ).sudo().action_confirm()
        return sale_order

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

    def _prepare_ic_sale_order_data(self, name, partner, company, direct_delivery_address):
        self.ensure_one()
        partner_addr = partner.sudo().address_get(["invoice", "delivery", "contact"])
        warehouse = company._ic_get_warehouse()
        if not warehouse:
            raise UserError(
                _(
                    "Configure a warehouse for company %(name)s in Inter-Company settings.",
                    name=company.name,
                )
            )
        shipping_partner_id = direct_delivery_address or partner_addr["delivery"]
        picking_warehouse_partner = self.picking_type_id.warehouse_id.partner_id
        if picking_warehouse_partner:
            shipping_partner_id = picking_warehouse_partner.id
        pricelist = partner.property_product_pricelist
        return {
            "name": self.env["ir.sequence"].sudo().next_by_code("sale.order") or "/",
            "company_id": company.id,
            "client_order_ref": name,
            "partner_id": partner.id,
            "pricelist_id": pricelist.id if pricelist else False,
            "partner_invoice_id": partner_addr["invoice"],
            "date_order": self.date_order,
            "fiscal_position_id": self.env["account.fiscal.position"]
            .sudo()
            .with_company(company)
            ._get_fiscal_position(partner)
            .id,
            "payment_term_id": partner.property_payment_term_id.id,
            "user_id": False,
            "auto_generated": True,
            "auto_purchase_order_id": self.id,
            "partner_shipping_id": shipping_partner_id,
            "commitment_date": self.date_planned,
            "warehouse_id": warehouse.id,
            "order_line": [],
        }

    @api.model
    def _prepare_ic_sale_order_line_data(self, line, company):
        price = line.price_unit or 0.0
        quantity = line.product_qty
        uom = line.product_uom
        if line.product_id:
            quantity = line.product_uom._compute_quantity(line.product_qty, line.product_id.uom_id)
            price = line.product_uom._compute_price(price, line.product_id.uom_id)
            uom = line.product_id.uom_id
        return {
            "name": line.name,
            "product_uom_qty": quantity,
            "product_id": line.product_id.id if line.product_id else False,
            "product_uom": uom.id if uom else False,
            "price_unit": price,
            "discount": line.discount or 0.0,
            "company_id": company.id,
            "display_type": line.display_type,
            "customer_lead": line.product_id.sale_delay if line.product_id else 0.0,
        }

    def _get_product_price_and_data(self, product):
        self.ensure_one()
        product_infos = super()._get_product_price_and_data(product)
        vendor_company = self.env["res.company"]._find_company_from_partner(self.partner_id.id)
        if not vendor_company:
            return product_infos
        line = self.env["purchase.order.line"].new(
            {
                "order_id": self.id,
                "product_id": product.id,
                "product_uom": product.uom_po_id.id or product.uom_id.id,
                "product_qty": 1.0,
                "company_id": self.company_id.id,
                "currency_id": self.currency_id.id,
            }
        )
        price = line._get_ic_seller_sale_price()
        if price is not None:
            product_infos["price"] = price
        return product_infos
