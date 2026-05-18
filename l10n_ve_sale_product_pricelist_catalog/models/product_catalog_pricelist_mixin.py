from odoo import models


class ProductCatalogPricelistMixin(models.AbstractModel):
    _name = "product.catalog.pricelist.mixin"
    _description = "Datos de listas de precios para el catálogo de productos"

    def _append_product_catalog_pricelists_data(self, record, res, products, date):
        company = record.company_id or record.env.company
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
