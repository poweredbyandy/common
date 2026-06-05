import pytz

from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    whatsapp_gateway_id = fields.Many2one(
        "mail.gateway",
        string="Gateway WhatsApp",
        domain=[("gateway_type", "=", "whatsapp")],
    )
    whatsapp_auto_create_contact = fields.Boolean(
        string="Crear contacto desde WhatsApp",
        default=True,
        help="Al recibir un mensaje de un número desconocido, se crea un contacto "
        "con el teléfono en lugar de un invitado anónimo.",
    )
    whatsapp_autoreply_enabled = fields.Boolean(
        string="Respuestas automáticas WhatsApp",
        default=False,
    )
    whatsapp_autoreply_default_message = fields.Text(
        string="Mensaje por defecto",
        help="Se envía cuando ninguna regla de horario coincide con el momento "
        "de recepción del mensaje.",
    )
    whatsapp_autoreply_rule_ids = fields.One2many(
        "pba.whatsapp.autoreply.rule",
        "company_id",
        string="Reglas de respuesta automática",
    )

    def _pba_whatsapp_local_datetime(self, dt=None):
        self.ensure_one()
        utc_dt = dt or fields.Datetime.now()
        if isinstance(utc_dt, str):
            utc_dt = fields.Datetime.from_string(utc_dt)
        tz_name = self.partner_id.tz or self.env.user.tz or "UTC"
        tz = pytz.timezone(tz_name)
        if utc_dt.tzinfo is None:
            utc_dt = pytz.utc.localize(utc_dt)
        return utc_dt.astimezone(tz)
