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
