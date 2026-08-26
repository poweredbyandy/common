from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    ic_free_qty_by_company = fields.Json(
        string="Free Qty Other Companies",
        compute="_compute_ic_free_qty_by_company",
    )

    def write(self, vals):
        res = super().write(vals)
        if self.env.context.get("skip_ic_so_write_sync"):
            return res
        sync_keys = {
            "price_unit",
            "product_uom_qty",
            "discount",
            "product_id",
            "product_uom",
            "name",
        }
        if sync_keys.intersection(vals):
            orders = self.mapped("order_id").filtered(lambda so: so.state in ("draft", "sent"))
            for order in orders:
                order._ic_try_create_purchase_order(force_draft=True)
        return res

    @api.depends("product_id", "product_uom", "company_id", "order_id.company_id")
    def _compute_ic_free_qty_by_company(self):
        companies = self.env["res.company"].sudo().search([])
        for line in self:
            if not line.product_id or not line.company_id:
                line.ic_free_qty_by_company = []
                continue
            rows = []
            uom = line.product_uom or line.product_id.uom_id
            for company in companies:
                if company == line.company_id:
                    continue
                product = line.product_id.sudo().with_company(company)
                free_qty = product.free_qty
                if uom and uom != line.product_id.uom_id:
                    free_qty = line.product_id.uom_id._compute_quantity(free_qty, uom)
                rows.append(
                    {
                        "company_id": company.id,
                        "company_name": company.name,
                        "free_qty": free_qty,
                    }
                )
            line.ic_free_qty_by_company = rows
