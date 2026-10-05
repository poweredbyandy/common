from odoo import fields, models

FLOW_TYPES = [
    ("inflow", "Inflow"),
    ("outflow", "Outflow"),
]

NATURES = [
    ("fixed", "Fixed"),
    ("variable", "Variable"),
]


class AccountTreasuryCategory(models.Model):
    _name = "account.treasury.category"
    _description = "Treasury Category"
    _order = "sequence, name"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    flow_type = fields.Selection(FLOW_TYPES, required=True, default="outflow")
    color = fields.Integer()
    active = fields.Boolean(default=True)
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
