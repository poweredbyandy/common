from odoo import fields, models


class PbaAlertDismissal(models.Model):
    _name = "pba.alert.dismissal"
    _description = "Alerta PBA marcada como hecha por usuario"
    _rec_name = "alert_id"

    alert_id = fields.Many2one(
        "pba.alert",
        required=True,
        ondelete="cascade",
        index=True,
    )
    res_model = fields.Char(required=True, index=True)
    res_id = fields.Integer(required=True, index=True)
    user_id = fields.Many2one(
        "res.users",
        required=True,
        ondelete="cascade",
        index=True,
    )

    _sql_constraints = [
        (
            "pba_alert_dismissal_unique",
            "UNIQUE(alert_id, res_model, res_id, user_id)",
            "Ya existe un registro de alerta atendida para este documento y usuario.",
        ),
    ]
