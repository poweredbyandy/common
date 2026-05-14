from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    partner_internal_note = fields.Html(
        related="partner_id.comment",
        string="Nota del cliente",
        readonly=True,
    )
