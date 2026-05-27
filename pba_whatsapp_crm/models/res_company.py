from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    whatsapp_crm_auto_lead = fields.Boolean(
        string="Crear lead desde WhatsApp",
        default=False,
        help="Crea una oportunidad CRM cuando llega un mensaje nuevo de WhatsApp.",
    )
    whatsapp_crm_team_id = fields.Many2one(
        "crm.team",
        string="Equipo de ventas WhatsApp",
    )
    whatsapp_crm_user_id = fields.Many2one(
        "res.users",
        string="Comercial WhatsApp",
    )
    whatsapp_crm_assign_equally = fields.Boolean(
        string="Asignar leads de forma equitativa",
        default=False,
        help="Distribuye nuevos leads de WhatsApp entre miembros del equipo "
        "en modalidad round-robin.",
    )
    whatsapp_crm_last_user_id = fields.Many2one(
        "res.users",
        string="Último comercial asignado WhatsApp",
        copy=False,
    )
