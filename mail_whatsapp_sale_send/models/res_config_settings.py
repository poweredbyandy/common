from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    quotation_mail_template_id = fields.Many2one(
        "mail.template",
        string="Quotation Email Template",
        domain=[("model", "=", "sale.order")],
        config_parameter="mail_whatsapp_sale_send.quotation_mail_template_id",
    )
    sale_mail_template_id = fields.Many2one(
        "mail.template",
        string="Confirmed Order Email Template",
        domain=[("model", "=", "sale.order")],
        config_parameter="mail_whatsapp_sale_send.sale_mail_template_id",
    )
    quotation_wa_account_id = fields.Many2one(
        "mail.whatsapp.account",
        string="Quotation WhatsApp Number",
        domain=[("active", "=", True)],
        config_parameter="mail_whatsapp_sale_send.quotation_wa_account_id",
    )
    quotation_wa_template_id = fields.Many2one(
        "mail.whatsapp.template",
        string="Quotation WhatsApp Template",
        domain="[('active', '=', True), ('wa_account_id', '=', quotation_wa_account_id), '|', ('model', '=', False), ('model', '=', 'sale.order')]",
        config_parameter="mail_whatsapp_sale_send.quotation_wa_template_id",
    )
    sale_wa_account_id = fields.Many2one(
        "mail.whatsapp.account",
        string="Confirmed Order WhatsApp Number",
        domain=[("active", "=", True)],
        config_parameter="mail_whatsapp_sale_send.sale_wa_account_id",
    )
    sale_wa_template_id = fields.Many2one(
        "mail.whatsapp.template",
        string="Confirmed Order WhatsApp Template",
        domain="[('active', '=', True), ('wa_account_id', '=', sale_wa_account_id), '|', ('model', '=', False), ('model', '=', 'sale.order')]",
        config_parameter="mail_whatsapp_sale_send.sale_wa_template_id",
    )
