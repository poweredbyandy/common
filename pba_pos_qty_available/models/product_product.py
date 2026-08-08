from odoo import _, api, models
from odoo.exceptions import AccessError, UserError

_PBA_FREE_QTY_RPC_LIMIT = 200


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _get_archived_combinations_per_product_tmpl_id(self, product_tmpl_ids):
        product_templates = self.env["product.template"].browse(
            product_tmpl_ids
        ).filtered("attribute_line_ids")
        return super()._get_archived_combinations_per_product_tmpl_id(
            product_templates.ids
        )

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields = super()._load_pos_data_fields(config_id)
        config = self.env["pos.config"].browse(config_id)
        if config.show_product_qty_available and "free_qty" not in fields:
            fields = list(fields) + ["free_qty"]
        return fields

    def _load_product_with_domain(self, domain, config_id, load_archived=False):
        config = self.env["pos.config"].browse(config_id)
        if config.show_product_qty_available and config.warehouse_id:
            self = self.with_context(warehouse_id=config.warehouse_id.id)
        return super()._load_product_with_domain(
            domain, config_id, load_archived=load_archived
        )

    def _process_pos_ui_product_product(self, products, config_id):
        super()._process_pos_ui_product_product(products, config_id)
        if not config_id.show_product_qty_available:
            return
        if not products:
            return
        product_ids = [product["id"] for product in products]
        sellable_map = self.env["pos.config"]._pba_pos_compute_sellable_qty(
            product_ids, config_id.warehouse_id
        )
        for product in products:
            product["free_qty"] = sellable_map.get(product["id"], 0.0)


    @api.model
    def get_pos_free_qty(self, product_ids, config_id):
        config = self.env["pos.config"].browse(config_id)
        if not config.exists():
            raise UserError(_("POS configuration not found."))
        if not config.show_product_qty_available:
            return {}
        if not self.env.user.has_group("point_of_sale.group_pos_user"):
            raise AccessError(_("You are not allowed to access POS stock quantities."))
        if not product_ids:
            return {}
        # Guard against accidental full-catalog RPC from the client.
        product_ids = list(dict.fromkeys(product_ids))[:_PBA_FREE_QTY_RPC_LIMIT]
        return self.env["pos.config"]._pba_pos_compute_sellable_qty(
            product_ids, config.warehouse_id
        )
