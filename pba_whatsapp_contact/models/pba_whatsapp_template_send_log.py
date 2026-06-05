from odoo import fields, models


class PbaWhatsappTemplateSendLog(models.Model):
    _name = "pba.whatsapp.template.send.log"
    _description = "Registro de envío de plantilla WhatsApp"
    _order = "sent_date desc"

    res_model = fields.Char(required=True, index=True)
    res_id = fields.Integer(required=True, index=True)
    template_id = fields.Many2one(
        "mail.whatsapp.template",
        required=True,
        ondelete="cascade",
    )
    sent_date = fields.Datetime(required=True, default=fields.Datetime.now)
    user_id = fields.Many2one("res.users", default=lambda self: self.env.user)

    _sql_constraints = [
        (
            "res_template_uniq",
            "unique(res_model, res_id, template_id)",
            "La plantilla ya fue registrada para este documento.",
        ),
    ]
