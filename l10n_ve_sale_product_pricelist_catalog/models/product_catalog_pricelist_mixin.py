from odoo import models


class ProductCatalogPricelistMixin(models.AbstractModel):
    _name = "product.catalog.pricelist.mixin"
    _description = "Datos de listas de precios para el catálogo de productos"

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
        company = record.company_id or record.env.company
        tax_included = company.product_catalog_price_tax_included
        partner = self._get_catalog_tax_partner(record) if tax_included else False
        fiscal_position = (
            self._get_catalog_fiscal_position(record, partner, company)
            if tax_included
            else self.env["account.fiscal.position"]
        )
        pricelists = record.env["product.pricelist"].search([("active", "=", True)])
        for pricelist in pricelists:
            prices = pricelist._get_products_price(
                products,
                quantity=1.0,
                date=date,
            )
            currency = pricelist.currency_id
            for product in products:
                price = prices.get(product.id, 0.0)
                if tax_included:
                    price = self._get_catalog_price_with_tax(
                        product,
                        price,
                        currency,
                        company,
                        partner,
                        fiscal_position,
                    )
                company_currency_price = currency._convert(
                    price,
                    company.currency_id,
                    company,
                    date,
                )
                if "pricelists" not in res[product.id]:
                    res[product.id]["pricelists"] = []
                res[product.id]["pricelists"].append(
                    {
                        "id": pricelist.id,
                        "name": pricelist.name + f" ({pricelist.currency_id.symbol})",
                        "price": price,
                        "company_currency_price": company_currency_price,
                        "currency_id": pricelist.currency_id.id,
                        "currency_symbol": pricelist.currency_id.symbol,
                        "company_currency_id": company.currency_id.id,
                        "company_currency_symbol": company.currency_id.symbol,
                    }
                )
        return res
