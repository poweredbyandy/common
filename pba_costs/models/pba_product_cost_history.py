from odoo import fields, models


class PbaProductCostHistory(models.Model):
    _name = "pba.product.cost.history"
    _description = "Historial de costos PBA"
    _order = "date desc, id desc"

    product_tmpl_id = fields.Many2one(
        "product.template",
        required=True,
        ondelete="cascade",
        index=True,
    )
    cost_type = fields.Selection(
        [
            ("freight", "Costo Flete"),
            ("tariff", "Costo Arancel"),
            ("operative", "Costo Operativo"),
            ("nationalization", "Costo Nacionalización"),
        ],
        required=True,
        index=True,
    )
    date = fields.Datetime(required=True, default=fields.Datetime.now)
    user_id = fields.Many2one("res.users", default=lambda self: self.env.user)
    amount = fields.Monetary(string="Costo", currency_field="currency_id")
    percent = fields.Float(string="% aplicado")
    currency_id = fields.Many2one(
        related="product_tmpl_id.cost_currency_id",
        store=True,
    )
    company_id = fields.Many2one(related="product_tmpl_id.company_id", store=True)
