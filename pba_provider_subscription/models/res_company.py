from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    pba_sla_hours_low = fields.Float(
        string="SLA Hours Low",
        default=336.0,
        help="Default: 2 weeks (336 hours).",
    )
    pba_sla_hours_normal = fields.Float(
        string="SLA Hours Normal",
        default=168.0,
        help="Default: 1 week (168 hours).",
    )
    pba_sla_hours_high = fields.Float(
        string="SLA Hours High",
        default=48.0,
        help="Default: 2 days (48 hours).",
    )
    pba_sla_hours_urgent = fields.Float(
        string="SLA Hours Urgent",
        default=5.0,
        help="Default: 5 hours.",
    )
    pba_sla_priority_mismatch_hours = fields.Float(
        string="Priority Mismatch Holgura Hours",
        default=24.0,
        help="Extra resolution slack when the customer overstates priority. Default: 1 day.",
    )

    def _pba_get_sla_hours(self, priority):
        self.ensure_one()
        mapping = {
            "0": self.pba_sla_hours_low,
            "1": self.pba_sla_hours_normal,
            "2": self.pba_sla_hours_high,
            "3": self.pba_sla_hours_urgent,
        }
        return mapping.get(priority or "1", self.pba_sla_hours_normal) or 0.0
