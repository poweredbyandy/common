from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MailWhatsappFollowup(models.TransientModel):
    _name = "mail.whatsapp.followup"
    _description = "Schedule WhatsApp Follow-up"

    res_model = fields.Char(string="Document Model", required=True)
    res_id = fields.Integer(string="Document ID", required=True)
    show_interest = fields.Boolean(default=True)
    delay_days = fields.Integer(
        string="Enviar en (días)",
        required=True,
        default=3,
        help="Number of days from today to schedule the follow-up activity.",
    )
    date_deadline = fields.Date(
        string="Fecha de seguimiento",
        compute="_compute_date_deadline",
        store=True,
        readonly=False,
    )
    interest = fields.Text(string="Intereses")
    message_body = fields.Text(
        string="Mensaje de seguimiento",
        compute="_compute_message_body",
        store=True,
        readonly=False,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Asignado a",
        required=True,
        default=lambda self: self.env.user,
    )
    activity_type_id = fields.Many2one(
        "mail.activity.type",
        string="Tipo de actividad",
        required=True,
        default=lambda self: self.env.ref(
            "mail_whatsapp.mail_activity_type_whatsapp_followup",
            raise_if_not_found=False,
        ),
    )

    def _get_record(self):
        self.ensure_one()
        if not self.res_model or not self.res_id:
            raise UserError(_("Missing related document."))
        if self.res_model not in self.env:
            raise UserError(_("Invalid model: %s") % self.res_model)
        record = self.env[self.res_model].browse(self.res_id).exists()
        if not record:
            raise UserError(_("The related record no longer exists."))
        if not hasattr(record, "activity_schedule"):
            raise UserError(
                _("Model %(model)s does not support activities.")
                % {"model": self.res_model}
            )
        return record

    @api.depends("delay_days")
    def _compute_date_deadline(self):
        today = fields.Date.context_today(self)
        for wizard in self:
            days = max(wizard.delay_days or 0, 0)
            wizard.date_deadline = today + timedelta(days=days)

    @api.depends("res_model", "res_id", "interest")
    def _compute_message_body(self):
        for wizard in self:
            wizard.message_body = False
            if (
                not wizard.res_model
                or not wizard.res_id
                or wizard.res_model not in wizard.env
            ):
                continue
            record = wizard.env[wizard.res_model].browse(wizard.res_id)
            if not record.exists() or not hasattr(
                record, "_get_whatsapp_followup_message"
            ):
                continue
            wizard.message_body = record._get_whatsapp_followup_message(
                interest=wizard.interest
            )

    def action_schedule(self):
        self.ensure_one()
        if self.delay_days < 0:
            raise UserError(_("Days must be zero or positive."))
        if not self.date_deadline:
            raise UserError(_("Please set a follow-up date."))
        if not self.activity_type_id:
            raise UserError(_("Please select an activity type."))

        record = self._get_record()
        if self.show_interest:
            record._whatsapp_followup_set_interest(self.interest)

        note = (
            self.message_body
            or record._get_whatsapp_followup_message(self.interest)
        ).replace("\n", "<br/>")
        record.activity_schedule(
            activity_type_id=self.activity_type_id.id,
            date_deadline=self.date_deadline,
            summary=record._whatsapp_followup_summary(self.interest),
            note=note,
            user_id=self.user_id.id,
            automated=True,
        )
        return {"type": "ir.actions.act_window_close"}
