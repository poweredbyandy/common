from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Command


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model
    def _pba_pos_convert_price(self, amount, from_currency, to_currency, company):
        if (
            not amount
            or not from_currency
            or not to_currency
            or from_currency == to_currency
        ):
            return amount or 0.0
        return from_currency._convert(
            amount,
            to_currency,
            company,
            fields.Date.context_today(self),
        )

    @api.model
    def create_quotation_from_pos(self, order_data):
        """Create a draft quotation from POS order data and return its id/name."""
        if not order_data:
            raise UserError(_("No order data was provided."))
        partner_id = order_data.get("partner_id")
        if not partner_id:
            raise UserError(
                _("You must select a customer before generating a quotation.")
            )
        lines_data = order_data.get("lines") or []
        if not lines_data:
            raise UserError(_("The POS order has no products."))

        partner = self.env["res.partner"].browse(partner_id).exists()
        if not partner:
            raise UserError(_("The selected customer no longer exists."))

        company = self.env.company
        if order_data.get("company_id"):
            company = (
                self.env["res.company"].browse(order_data["company_id"]).exists()
                or self.env.company
            )

        config = self.env["pos.config"]
        if order_data.get("config_id"):
            config = self.env["pos.config"].browse(order_data["config_id"]).exists()

        pricelist = self.env["product.pricelist"]
        if order_data.get("pricelist_id"):
            pricelist = (
                self.env["product.pricelist"].browse(order_data["pricelist_id"]).exists()
            )

        pos_currency = company.currency_id
        if order_data.get("pos_currency_id"):
            pos_currency = (
                self.env["res.currency"].browse(order_data["pos_currency_id"]).exists()
                or pos_currency
            )
        elif config:
            pos_currency = config.currency_id or pos_currency

        prepared_lines = []
        for line in lines_data:
            product_id = line.get("product_id")
            if not product_id:
                continue
            product = self.env["product.product"].browse(product_id).exists()
            if not product:
                raise UserError(
                    _("Product with ID %s was not found.") % product_id
                )
            prepared_lines.append((product, line))

        if not prepared_lines:
            raise UserError(_("The POS order has no valid products."))

        so_vals = {
            "partner_id": partner.id,
            "company_id": company.id,
            "origin": order_data.get("pos_reference") or _("Point of Sale"),
            "client_order_ref": order_data.get("pos_reference") or False,
            "note": order_data.get("note") or False,
        }
        if order_data.get("fiscal_position_id"):
            so_vals["fiscal_position_id"] = order_data["fiscal_position_id"]
        if order_data.get("user_id"):
            so_vals["user_id"] = order_data["user_id"]
        if config and config.warehouse_id:
            so_vals["warehouse_id"] = config.warehouse_id.id
        if config and "crm_team_id" in config._fields and config.crm_team_id:
            so_vals["team_id"] = config.crm_team_id.id

        order = self.with_company(company).sudo().create(so_vals)

        if pricelist:
            order.write({"pricelist_id": pricelist.id})

        target_currency = order.currency_id or company.currency_id
        SaleOrderLine = self.env["sale.order.line"].with_company(company).sudo()

        for product, line in prepared_lines:
            price_unit = self._pba_pos_convert_price(
                line.get("price_unit") or 0.0,
                pos_currency,
                target_currency,
                company,
            )
            discount = line.get("discount") or 0.0
            tax_ids = line.get("tax_ids") or []
            line_vals = {
                "order_id": order.id,
                "product_id": product.id,
                "product_uom_qty": line.get("qty") or 1.0,
                "name": line.get("name")
                or product.get_product_multiline_description_sale(),
            }
            if line.get("product_uom_id"):
                line_vals["product_uom"] = line["product_uom_id"]
            sol = SaleOrderLine.create(line_vals)
            write_vals = {
                "price_unit": price_unit,
                "technical_price_unit": 0.0,
                "discount": discount,
            }
            if tax_ids:
                write_vals["tax_id"] = [Command.set(tax_ids)]
            sol.write(write_vals)

        return {
            "id": order.id,
            "name": order.name,
            "currency_id": order.currency_id.id,
            "currency_name": order.currency_id.name,
            "pricelist_id": order.pricelist_id.id,
        }
