from odoo import _, api, fields, models
from odoo.osv import expression


class PbaProductCatalogViewer(models.Model):
    _name = "pba.product.catalog.viewer"
    _description = "Visor de catálogo de productos"
    _inherit = ["product.catalog.mixin"]

    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    user_id = fields.Many2one(
        "res.users",
        required=True,
        default=lambda self: self.env.user,
        index=True,
    )
    pricelist_id = fields.Many2one(
        "product.pricelist",
        string="Lista de precios",
        compute="_compute_pricelist_id",
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="pricelist_id.currency_id",
    )

    _sql_constraints = [
        (
            "pba_product_catalog_viewer_user_company_uniq",
            "unique(user_id, company_id)",
            "Solo puede existir un visor de catálogo por usuario y compañía.",
        ),
    ]

    @api.depends("user_id", "user_id.partner_id.property_product_pricelist", "company_id")
    def _compute_pricelist_id(self):
        for viewer in self:
            partner = viewer.user_id.partner_id.with_company(viewer.company_id)
            pricelist = partner.property_product_pricelist
            if not pricelist:
                pricelist_map = self.env["product.pricelist"].with_company(
                    viewer.company_id
                )._get_partner_pricelist_multi(partner.ids)
                pricelist = pricelist_map.get(partner.id)
            viewer.pricelist_id = pricelist

    @api.model
    def get_or_create_viewer(self):
        viewer = self.search(
            [
                ("user_id", "=", self.env.uid),
                ("company_id", "=", self.env.company.id),
            ],
            limit=1,
        )
        if not viewer:
            viewer = self.create({})
        return viewer

    def action_open_catalog(self):
        self.ensure_one()
        return self.action_add_from_catalog()

    def action_add_from_catalog(self):
        action = super().action_add_from_catalog()
        action["name"] = _("Catálogo")
        return action

    def _is_readonly(self):
        return True

    def _get_product_catalog_domain(self):
        return expression.AND(
            [
                super()._get_product_catalog_domain(),
                [("sale_ok", "=", True)],
            ]
        )

    def _get_product_catalog_record_lines(self, product_ids, child_field=False, **kwargs):
        return {}

    def _get_product_catalog_order_data(self, products, **kwargs):
        self.ensure_one()
        res = super()._get_product_catalog_order_data(products, **kwargs)
        if self.pricelist_id:
            prices = self.pricelist_id._get_products_price(
                products,
                quantity=1.0,
                date=fields.Datetime.now(),
            )
            for product in products:
                res[product.id]["price"] = prices.get(product.id, 0.0)
        for product in products:
            res[product.id]["readOnly"] = True
        return self.env[
            "product.catalog.pricelist.mixin"
        ]._append_product_catalog_pricelists_data(
            self,
            res,
            products,
            fields.Datetime.now(),
        )

    def _update_order_line_info(self, product_id, quantity, **kwargs):
        self.ensure_one()
        product = self.env["product.product"].browse(product_id)
        if not self.pricelist_id:
            return product.lst_price
        return self.pricelist_id._get_product_price(
            product,
            quantity=quantity or 1.0,
            date=fields.Datetime.now(),
            **kwargs,
        )

    def _get_action_add_from_catalog_extra_context(self):
        self.ensure_one()
        currency = self.currency_id or self.company_id.currency_id
        return {
            **super()._get_action_add_from_catalog_extra_context(),
            "order_id": self.id,
            "pba_product_catalog_standalone": True,
            "product_catalog_currency_id": currency.id,
            "product_catalog_digits": self.env["product.pricelist.item"]._fields[
                "fixed_price"
            ].get_digits(self.env),
        }
