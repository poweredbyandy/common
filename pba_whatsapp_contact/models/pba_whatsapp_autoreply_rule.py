from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import pytz


class PbaWhatsappAutoreplyRule(models.Model):
    _name = "pba.whatsapp.autoreply.rule"
    _description = "Regla de respuesta automática WhatsApp"
    _order = "sequence, id"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    sequence = fields.Integer(default=10)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="cascade",
    )
    message = fields.Text(required=True)
    monday = fields.Boolean(string="Lunes", default=True)
    tuesday = fields.Boolean(string="Martes", default=True)
    wednesday = fields.Boolean(string="Miércoles", default=True)
    thursday = fields.Boolean(string="Jueves", default=True)
    friday = fields.Boolean(string="Viernes", default=True)
    saturday = fields.Boolean(string="Sábado", default=False)
    sunday = fields.Boolean(string="Domingo", default=False)
    hour_from = fields.Float(
        string="Desde",
        default=8.0,
        help="Hora de inicio en formato decimal (8.0 = 08:00, 17.5 = 17:30).",
    )
    hour_to = fields.Float(
        string="Hasta",
        default=17.0,
        help="Hora de fin en formato decimal (17.0 = 17:00).",
    )

    @api.constrains("hour_from", "hour_to")
    def _check_hours(self):
        for rule in self:
            if not (0.0 <= rule.hour_from < 24.0):
                raise ValidationError(_("La hora de inicio debe estar entre 00:00 y 23:59."))
            if not (0.0 < rule.hour_to <= 24.0):
                raise ValidationError(_("La hora de fin debe estar entre 00:01 y 24:00."))
            if rule.hour_from >= rule.hour_to:
                raise ValidationError(
                    _("La hora de inicio debe ser anterior a la hora de fin.")
                )

    @api.constrains(
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
        "saturday",
        "sunday",
    )
    def _check_weekdays(self):
        for rule in self:
            if not any(
                (
                    rule.monday,
                    rule.tuesday,
                    rule.wednesday,
                    rule.thursday,
                    rule.friday,
                    rule.saturday,
                    rule.sunday,
                )
            ):
                raise ValidationError(_("Debe seleccionar al menos un día de la semana."))

    def _pba_matches_schedule(self, weekday, hour_float):
        self.ensure_one()
        weekday_flags = (
            self.monday,
            self.tuesday,
            self.wednesday,
            self.thursday,
            self.friday,
            self.saturday,
            self.sunday,
        )
        if weekday < 0 or weekday > 6 or not weekday_flags[weekday]:
            return False
        return self.hour_from <= hour_float < self.hour_to

    def _pba_get_local_datetime_for_rule(self, company, dt=None):
        self.ensure_one()
        utc_dt = dt or fields.Datetime.now()
        if isinstance(utc_dt, str):
            utc_dt = fields.Datetime.from_string(utc_dt)
        if utc_dt.tzinfo is None:
            utc_dt = pytz.utc.localize(utc_dt)
        tz_name = (
            self.write_uid.tz
            or self.create_uid.tz
            or company.partner_id.tz
            or self.env.user.tz
            or "UTC"
        )
        return utc_dt.astimezone(pytz.timezone(tz_name))

    @api.model
    def _pba_get_message_for_company(self, company, dt=None):
        company = company or self.env.company
        if not company.whatsapp_autoreply_enabled:
            return False
        rules = self.search(
            [
                ("company_id", "=", company.id),
                ("active", "=", True),
            ],
            order="sequence, id",
        )
        for rule in rules:
            local_dt = rule._pba_get_local_datetime_for_rule(company, dt)
            weekday = local_dt.weekday()
            hour_float = local_dt.hour + local_dt.minute / 60.0 + local_dt.second / 3600.0
            if rule._pba_matches_schedule(weekday, hour_float):
                return rule.message
        if rules:
            return False
        return company.whatsapp_autoreply_default_message or False
