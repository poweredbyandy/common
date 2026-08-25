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

    def _action_confirm(self):
        res = super()._action_confirm()
        for order in self:
            if not order.company_id:
                continue
            company = self.env["res.company"]._find_company_from_partner(order.partner_id.id)
            if company and company.ic_po_from_so and not order.auto_generated:
                order.sudo()._ic_create_purchase_order(company)
        return res

    def _ic_create_purchase_order(self, company):
        self.ensure_one()
        rights = ["purchase"]
        if company.ic_po_state == "confirmed":
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
            .with_context(allowed_company_ids=company.ids)
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
        if not self.client_order_ref:
            self.sudo().with_company(self.company_id).write(
                {"client_order_ref": purchase_order.name}
            )
        if company.ic_po_state == "confirmed":
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
        warehouse = company.ic_warehouse_id
        if not warehouse or warehouse.company_id != company:
            raise UserError(
                _(
                    "Configure a warehouse for company %(name)s in Inter-Company settings.",
                    name=company.name,
                )
            )
        picking_type = company.ic_receipt_type_id
        if not picking_type:
            picking_type = self.env["stock.picking.type"].search(
                [("code", "=", "incoming"), ("warehouse_id", "=", warehouse.id)],
                limit=1,
            )
        if not picking_type:
            picking_type = (
                self.env["purchase.order"]
                .with_user(company.ic_user_id)
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
