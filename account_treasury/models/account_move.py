from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    treasury_forecast_id = fields.Many2one(
        "account.treasury.forecast",
        string="Treasury Forecast",
        index="btree_not_null",
        copy=False,
        readonly=True,
        ondelete="set null",
    )
