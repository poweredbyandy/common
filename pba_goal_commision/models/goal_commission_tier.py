from odoo import api, fields, models
from odoo.exceptions import ValidationError


class GoalCommissionTier(models.Model):
    _name = "goal.commission.tier"
    _description = "Tramo de Comision por Meta"
    _order = "sequence, min_amount, id"

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    name = fields.Char(required=True)
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        required=True,
        domain=[("user_ids", "!=", False)],
        ondelete="cascade",
    )
    company_id = fields.Many2one(
        related="partner_id.company_id",
        store=True,
    )
    currency_id = fields.Many2one(
        related="partner_id.goal_commission_currency_id",
        store=True,
    )
    min_amount = fields.Monetary(
        string="Monto Minimo",
        currency_field="currency_id",
        required=True,
    )
    max_amount = fields.Monetary(
        string="Monto Maximo",
        currency_field="currency_id",
    )
    commission_percent = fields.Float(
        string="% Comision",
        required=True,
    )

    @api.constrains("min_amount", "max_amount", "commission_percent")
    def _check_values(self):
        for tier in self:
            if tier.min_amount < 0:
                raise ValidationError("El monto minimo no puede ser negativo.")
            if tier.max_amount and tier.max_amount <= tier.min_amount:
                raise ValidationError("El monto maximo debe ser mayor al minimo.")
            if tier.commission_percent < 0:
                raise ValidationError("El porcentaje de comision no puede ser negativo.")
