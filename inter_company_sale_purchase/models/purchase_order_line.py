from odoo import api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    ic_qty_available = fields.Float(
        string="Vendor Qty On Hand",
        compute="_compute_ic_stock",
        digits="Product Unit of Measure",
    )
    ic_virtual_available = fields.Float(
        string="Vendor Forecasted Qty",
        compute="_compute_ic_stock",
        digits="Product Unit of Measure",
    )
    is_intercompany_vendor = fields.Boolean(
        compute="_compute_is_intercompany_vendor",
    )

    @api.depends("partner_id")
    def _compute_is_intercompany_vendor(self):
        Company = self.env["res.company"]
        for line in self:
            line.is_intercompany_vendor = bool(
                line.partner_id and Company._find_company_from_partner(line.partner_id.id)
            )

    @api.depends(
        "product_id",
        "product_uom",
        "partner_id",
        "company_id",
        "order_id.partner_id",
    )
    def _compute_ic_stock(self):
        Company = self.env["res.company"]
        for line in self:
            vendor_company = (
                Company._find_company_from_partner(line.partner_id.id)
                if line.partner_id
                else Company.browse()
            )
            if not line.product_id or not vendor_company:
                line.ic_qty_available = 0.0
                line.ic_virtual_available = 0.0
                continue
            product = line.product_id.sudo().with_company(vendor_company)
            if vendor_company.ic_warehouse_id:
                product = product.with_context(warehouse_id=vendor_company.ic_warehouse_id.id)
            qty_available = product.qty_available
            virtual_available = product.virtual_available
            uom = line.product_uom or line.product_id.uom_po_id
            if uom and uom != line.product_id.uom_id:
                qty_available = line.product_id.uom_id._compute_quantity(qty_available, uom)
                virtual_available = line.product_id.uom_id._compute_quantity(
                    virtual_available, uom
                )
            line.ic_qty_available = qty_available
            line.ic_virtual_available = virtual_available

    def _get_ic_vendor_company(self):
        self.ensure_one()
        if not self.partner_id:
            return self.env["res.company"]
        return self.env["res.company"]._find_company_from_partner(self.partner_id.id)

    def _get_ic_seller_sale_price(self):
        self.ensure_one()
        vendor_company = self._get_ic_vendor_company()
        if not vendor_company or not self.product_id:
            return None
        customer = self.company_id.partner_id.sudo().with_company(vendor_company)
        pricelist = customer.property_product_pricelist
        product = self.product_id.sudo().with_company(vendor_company)
        uom = self.product_uom or product.uom_po_id or product.uom_id
        quantity = self.product_qty or 1.0
        date = self.order_id.date_order or fields.Datetime.now()
        if pricelist:
            price = pricelist.sudo().with_company(vendor_company)._get_product_price(
                product,
                quantity,
                currency=self.currency_id,
                uom=uom,
                date=date,
            )
        else:
            price = product.uom_id._compute_price(product.list_price, uom)
            product_currency = product.currency_id or vendor_company.currency_id
            if product_currency and self.currency_id and product_currency != self.currency_id:
                price = product_currency._convert(
                    price,
                    self.currency_id,
                    self.company_id,
                    fields.Date.to_date(date),
                    False,
                )
        return price

    @api.depends("product_qty", "product_uom", "company_id", "order_id.partner_id")
    def _compute_price_unit_and_date_planned_and_name(self):
        super()._compute_price_unit_and_date_planned_and_name()
        for line in self:
            if not line.product_id or line.invoice_lines or not line.company_id:
                continue
            price = line._get_ic_seller_sale_price()
            if price is None:
                continue
            line.price_unit = price
            line.discount = 0.0
