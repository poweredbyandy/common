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

    def button_approve(self, force=False):
        res = super().button_approve(force=force)
        for order in self:
            company = self.env["res.company"]._find_company_from_partner(order.partner_id.id)
            if company and company.ic_so_from_po and not order.auto_generated:
                order.with_user(company.ic_user_id).with_company(company).with_context(
                    default_company_id=company.id,
                    allowed_company_ids=company.ids,
                )._ic_create_sale_order(company)
        return res

    def _ic_create_sale_order(self, company):
        self.ensure_one()
        ic_user = company.ic_user_id
        if not ic_user:
            raise UserError(
                _("Provide one user for inter-company relation for %(name)s.", name=company.name)
            )
        if not self.env["sale.order"].with_user(ic_user).has_access("create"):
            raise UserError(
                _(
                    "Inter-company user of company %(name)s does not have enough access rights.",
                    name=company.name,
                )
            )
        self._ic_check_shared_products(company)
        company_partner = self.company_id.partner_id.with_user(ic_user)
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
            .with_context(allowed_company_ids=company.ids)
            .with_user(ic_user)
            .create(sale_order_data)
        )
        sale_order.message_post(
            body=_(
                "Automatically generated from %(origin)s of company %(company)s.",
                origin=self.name,
                company=self.company_id.name,
            )
        )
        if not self.partner_ref:
            self.sudo().with_company(self.company_id).write({"partner_ref": sale_order.name})
        if company.ic_so_state == "confirmed":
            sale_order.with_user(ic_user).action_confirm()
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
