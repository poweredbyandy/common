from datetime import datetime, timedelta, time

import pytz

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    pba_sla_hours_low = fields.Float(
        string="SLA Business Hours Low",
        default=80.0,
        help="Default: 2 business weeks (10 x 8h = 80).",
    )
    pba_sla_hours_normal = fields.Float(
        string="SLA Business Hours Normal",
        default=40.0,
        help="Default: 1 business week (5 x 8h = 40).",
    )
    pba_sla_hours_high = fields.Float(
        string="SLA Business Hours High",
        default=16.0,
        help="Default: 2 business days (2 x 8h = 16).",
    )
    pba_sla_hours_urgent = fields.Float(
        string="SLA Business Hours Urgent",
        default=5.0,
        help="Default: 5 business hours.",
    )
    pba_sla_priority_mismatch_hours = fields.Float(
        string="Priority Mismatch Holgura Hours",
        default=8.0,
        help="Extra business hours when the customer overstates priority. Default: 1 business day.",
    )
    pba_sla_hour_from = fields.Float(
        string="Business Hour From",
        default=9.0,
        help="Workday start hour (default 9:00).",
    )
    pba_sla_hour_to = fields.Float(
        string="Business Hour To",
        default=17.0,
        help="Workday end hour (default 17:00).",
    )
    pba_sla_timezone = fields.Char(
        string="SLA Timezone",
        default="America/Caracas",
        help="Timezone used to compute business hours and deadlines.",
    )
    pba_sla_leave_ids = fields.One2many(
        "pba.sla.leave",
        "company_id",
        string="Unavailable Days",
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

    def _pba_get_workday_hours(self):
        self.ensure_one()
        start = float(self.pba_sla_hour_from or 9.0)
        end = float(self.pba_sla_hour_to or 17.0)
        return max(end - start, 0.0) or 8.0

    def _pba_get_sla_tz(self):
        self.ensure_one()
        tz_name = self.pba_sla_timezone or self.partner_id.tz or "UTC"
        try:
            return pytz.timezone(tz_name)
        except Exception:
            return pytz.UTC

    def _pba_float_to_time(self, value):
        hours = int(value)
        minutes = int(round((value - hours) * 60))
        if minutes >= 60:
            hours += 1
            minutes = 0
        return time(hour=min(hours, 23), minute=min(minutes, 59))

    def _pba_get_leave_dates(self, date_start=None, date_end=None):
        self.ensure_one()
        domain = [
            ("company_id", "=", self.id),
            ("active", "=", True),
        ]
        if date_start:
            domain.append(("date_to", ">=", date_start))
        if date_end:
            domain.append(("date_from", "<=", date_end))
        leaves = self.env["pba.sla.leave"].sudo().search(domain)
        blocked = set()
        for leave in leaves:
            current = leave.date_from
            while current <= leave.date_to:
                blocked.add(current)
                current += timedelta(days=1)
        return blocked

    def _pba_is_working_day(self, day, leave_dates=None):
        self.ensure_one()
        if day.weekday() >= 5:
            return False
        if leave_dates is None:
            leave_dates = self._pba_get_leave_dates(day, day)
        return day not in leave_dates

    def _pba_day_bounds(self, day):
        self.ensure_one()
        start_t = self._pba_float_to_time(self.pba_sla_hour_from or 9.0)
        end_t = self._pba_float_to_time(self.pba_sla_hour_to or 17.0)
        return (
            datetime.combine(day, start_t),
            datetime.combine(day, end_t),
        )

    def _pba_next_working_day(self, day, leave_dates):
        self.ensure_one()
        current = day + timedelta(days=1)
        for _dummy in range(0, 370):
            if self._pba_is_working_day(current, leave_dates):
                return current
            current += timedelta(days=1)
        return current

    def _pba_add_business_hours(self, start_dt, hours):
        """Add business hours to a UTC-naive datetime and return UTC-naive deadline."""
        self.ensure_one()
        hours = float(hours or 0.0)
        if not start_dt or hours <= 0:
            return start_dt
        if isinstance(start_dt, str):
            start_dt = fields.Datetime.from_string(start_dt)

        tz = self._pba_get_sla_tz()
        local_start = pytz.UTC.localize(start_dt, is_dst=False).astimezone(tz)
        leave_dates = self._pba_get_leave_dates(
            local_start.date(),
            local_start.date() + timedelta(days=max(int(hours) + 60, 90)),
        )

        current = local_start.replace(tzinfo=None)
        remaining = hours
        safety = 0
        while remaining > 1e-9 and safety < 10000:
            safety += 1
            day = current.date()
            if not self._pba_is_working_day(day, leave_dates):
                next_day = self._pba_next_working_day(day, leave_dates)
                day_start, _day_end = self._pba_day_bounds(next_day)
                current = day_start
                continue

            day_start, day_end = self._pba_day_bounds(day)
            if current < day_start:
                current = day_start
            if current >= day_end:
                next_day = self._pba_next_working_day(day, leave_dates)
                next_start, _next_end = self._pba_day_bounds(next_day)
                current = next_start
                continue

            available = (day_end - current).total_seconds() / 3600.0
            if remaining <= available:
                current = current + timedelta(hours=remaining)
                remaining = 0.0
            else:
                remaining -= available
                next_day = self._pba_next_working_day(day, leave_dates)
                next_start, _next_end = self._pba_day_bounds(next_day)
                current = next_start

        aware_local = tz.localize(current, is_dst=False)
        return aware_local.astimezone(pytz.UTC).replace(tzinfo=None)
