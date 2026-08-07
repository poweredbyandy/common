from odoo import _, models
from odoo.tools import html2plaintext


class MailActivityMixin(models.AbstractModel):
    _inherit = "mail.activity.mixin"

    def action_whatsapp_schedule_followup(self):
        """Open the reusable WhatsApp follow-up scheduling wizard."""
        self.ensure_one()
        activity_type = self._whatsapp_followup_default_activity_type()
        user = self._whatsapp_followup_default_user()
        return {
            "name": _("Programar seguimiento WhatsApp"),
            "type": "ir.actions.act_window",
            "res_model": "mail.whatsapp.followup",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_res_model": self._name,
                "default_res_id": self.id,
                "default_delay_days": self._whatsapp_followup_default_delay_days(),
                "default_interest": self._whatsapp_followup_get_interest(),
                "default_user_id": user.id if user else self.env.user.id,
                "default_activity_type_id": activity_type.id if activity_type else False,
                "default_show_interest": self._whatsapp_followup_use_interest(),
            },
        }

    def _whatsapp_followup_use_interest(self):
        return True

    def _whatsapp_followup_default_delay_days(self):
        return 3

    def _whatsapp_followup_default_activity_type(self):
        return self.env.ref(
            "mail_whatsapp.mail_activity_type_whatsapp_followup",
            raise_if_not_found=False,
        )

    def _whatsapp_followup_default_user(self):
        if "user_id" in self._fields and self.user_id:
            return self.user_id
        return self.env.user

    def _whatsapp_followup_get_contact_name(self):
        self.ensure_one()
        if "partner_id" in self._fields and self.partner_id:
            return self.partner_id.name
        if "contact_name" in self._fields and self.contact_name:
            return self.contact_name
        return self.display_name

    def _whatsapp_followup_get_interest(self):
        self.ensure_one()
        if "whatsapp_followup_interest_preview" in self.env.context:
            return self.env.context.get("whatsapp_followup_interest_preview")
        return False

    def _whatsapp_followup_set_interest(self, interest):
        """Persist interest/topic on the record. Override in specific modules."""
        return True

    def _whatsapp_followup_summary(self, interest=None):
        self.ensure_one()
        interest_text = (
            interest if interest is not None else self._whatsapp_followup_get_interest()
        ) or ""
        interest_text = (interest_text or self.display_name or "")[:80]
        return _("Seguimiento WhatsApp: %(interest)s") % {"interest": interest_text}

    def _get_whatsapp_followup_message(self, interest=None):
        """Preview of the WhatsApp follow-up template for the current record."""
        self.ensure_one()
        record = self
        if interest is not None:
            record = self.with_context(whatsapp_followup_interest_preview=interest)

        account = self.env["mail.whatsapp.composer"]._default_wa_account()
        template = self.env[
            "mail.whatsapp.template"
        ]._ensure_interest_followup_template(account)
        if template:
            return html2plaintext(template._get_preview_html(record) or "")

        contact = record._whatsapp_followup_get_contact_name()
        interest_text = (record._whatsapp_followup_get_interest() or "").strip() or _(
            "nuestros productos/servicios"
        )
        greeting = _("Hola %(name)s,", name=contact) if contact else _("Hola,")
        return _(
            "%(greeting)s nos escribiste por WhatsApp porque querías saber "
            "acerca de: %(interest)s. ¿Sigues interesado/a?"
        ) % {
            "greeting": greeting,
            "interest": interest_text,
        }
