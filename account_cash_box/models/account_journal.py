from odoo import fields, models, _


class AccountJournal(models.Model):
    _inherit = "account.journal"

    cash_box_ids = fields.One2many(
        "account.cash.box",
        "journal_id",
    )

    def action_open_cash_box(self):
        self.ensure_one()
        box = self.cash_box_ids[:1]
        if not box:
            return {
                "type": "ir.actions.act_window",
                "name": _("Cash Box"),
                "res_model": "account.cash.box",
                "view_mode": "form",
                "views": [(False, "form")],
                "context": {
                    "default_journal_id": self.id,
                    "default_company_id": self.company_id.id,
                    "default_name": self.name,
                },
            }
        return box.action_open_form()
