from odoo import models


class ProductCatalogPricelistMixin(models.AbstractModel):
    _inherit = "product.catalog.pricelist.mixin"

    def _get_catalog_tax_partner(self, record):
        if "partner_id" in record._fields and record.partner_id:
            return record.partner_id
        if "user_id" in record._fields and record.user_id:
            return record.user_id.partner_id
        return self.env["res.partner"]

    def _get_catalog_fiscal_position(self, record, partner, company):
        if record._name == "sale.order" and record.fiscal_position_id:
            return record.fiscal_position_id
        if partner:
            return self.env["account.fiscal.position"].with_company(
                company
            )._get_fiscal_position(partner)
        return self.env["account.fiscal.position"]

    def _get_catalog_price_with_tax(
        self, product, price, currency, company, partner, fiscal_position
    ):
        taxes = product.taxes_id._filter_taxes_by_company(company)
        if fiscal_position and taxes:
            taxes = fiscal_position.map_tax(taxes)
        if not taxes:
            return price
        return taxes.compute_all(
            price,
            currency=currency,
            product=product,
            partner=partner,
        )["total_included"]

    def _append_product_catalog_pricelists_data(self, record, res, products, date):
        res = super()._append_product_catalog_pricelists_data(
            record, res, products, date
        )
        company = record.company_id or record.env.company
        if not company.pba_product_catalog_price_tax_included:
            return res
        partner = self._get_catalog_tax_partner(record)
        fiscal_position = self._get_catalog_fiscal_position(record, partner, company)
        currency_model = record.env["res.currency"]
        for product in products:
            product_data = res.get(product.id) or {}
            for pricelist_data in product_data.get("pricelists") or []:
                currency = currency_model.browse(pricelist_data["currency_id"])
                price = self._get_catalog_price_with_tax(
                    product,
                    pricelist_data["price"],
                    currency,
                    company,
                    partner,
                    fiscal_position,
                )
                pricelist_data["price"] = price
                pricelist_data["company_currency_price"] = currency._convert(
                    price,
                    company.currency_id,
                    company,
                    date,
                )
        return res
