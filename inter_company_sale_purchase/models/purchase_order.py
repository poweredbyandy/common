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
    is_intercompany_vendor = fields.Boolean(
        compute="_compute_is_intercompany_vendor",
    )

    @api.depends("partner_id")
    def _compute_is_intercompany_vendor(self):
        Company = self.env["res.company"]
        for order in self:
            order.is_intercompany_vendor = bool(
                order.partner_id and Company._find_company_from_partner(order.partner_id.id)
            )

    def button_approve(self, force=False):
        res = super().button_approve(force=force)
        for order in self:
            company = self.env["res.company"]._find_company_from_partner(order.partner_id.id)
            if company and company.ic_so_from_po and not order.auto_generated:
                order.sudo()._ic_create_sale_order(company)
        return res

    def _ic_create_sale_order(self, company):
        self.ensure_one()
        rights = ["sale"]
        if company.ic_so_state == "confirmed":
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
        if not self.partner_ref:
            self.sudo().with_company(self.company_id).write({"partner_ref": sale_order.name})
        if company.ic_so_state == "confirmed":
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
        warehouse = company.ic_warehouse_id
        if not warehouse or warehouse.company_id != company:
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
        return {
            "name": self.env["ir.sequence"].sudo().next_by_code("sale.order") or "/",
            "company_id": company.id,
            "client_order_ref": name,
            "partner_id": partner.id,
            "pricelist_id": partner.property_product_pricelist.id,
            "partner_invoice_id": partner_addr["invoice"],
            "date_order": self.date_order,
            "fiscal_position_id": self.env["account.fiscal.position"]
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

