from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    excess_refund_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Excess Refund Journal",
        check_company=True,
        domain="[('type', 'in', ('bank', 'cash', 'credit'))]",
        help="Default journal used when refunding payment excesses from "
        "customer invoices and vendor bills.",
    )
