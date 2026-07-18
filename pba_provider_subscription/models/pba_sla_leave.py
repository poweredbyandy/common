from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PbaSlaLeave(models.Model):
    _name = "pba.sla.leave"
    _description = "SLA Unavailable Day"
    _order = "date_from desc, id desc"

    name = fields.Char(required=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )
    date_from = fields.Date(required=True, index=True)
    date_to = fields.Date(required=True, index=True)
    active = fields.Boolean(default=True)

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for leave in self:
            if leave.date_from and leave.date_to and leave.date_from > leave.date_to:
                raise ValidationError(
                    _("The end date must be after or equal to the start date.")
                )

    def write(self, vals):
        res = super().write(vals)
        self._pba_recompute_ticket_deadlines()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        leaves = super().create(vals_list)
        leaves._pba_recompute_ticket_deadlines()
        return leaves

    def unlink(self):
        companies = self.mapped("company_id")
        res = super().unlink()
        tickets = self.env["pba.support.ticket"].sudo().search(
            [("company_id", "in", companies.ids)]
        )
        tickets._compute_sla_deadline()
        return res

    def _pba_recompute_ticket_deadlines(self):
        companies = self.mapped("company_id")
        if not companies:
            return
        tickets = self.env["pba.support.ticket"].sudo().search(
            [("company_id", "in", companies.ids)]
        )
        tickets._compute_sla_deadline()
