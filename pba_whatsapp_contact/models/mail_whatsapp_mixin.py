from odoo import _, api, fields, models
from odoo.exceptions import UserError


class MailWhatsappMixin(models.AbstractModel):
    _name = "mail.whatsapp.mixin"
    _description = "Envío WhatsApp desde documentos"

    pba_whatsapp_show_button = fields.Boolean(
        compute="_compute_pba_whatsapp_show_button",
    )

    @api.depends()
    def _compute_pba_whatsapp_show_button(self):
        for record in self:
            record.pba_whatsapp_show_button = bool(
                record._pba_whatsapp_get_template_options()
            )

    def _pba_whatsapp_get_record_company(self):
        self.ensure_one()
        if "company_id" in self._fields and self.company_id:
            return self.company_id
        return self.env.company

    def _pba_whatsapp_search_model_templates(self, extra_domain=None):
        self.ensure_one()
        company = self._pba_whatsapp_get_record_company()
        domain = [
            ("model_id.model", "=", self._name),
            ("state", "in", ("approved", "pending")),
        ]
        gateway = company.whatsapp_gateway_id
        if gateway:
            domain.append(("gateway_id", "=", gateway.id))
        elif company:
            domain.append(("company_id", "in", (company.id, False)))
        if extra_domain:
            domain.extend(extra_domain)
        return self.env["mail.whatsapp.template"].search(domain, order="name, id")

    def _pba_whatsapp_filter_templates_by_record(self, templates):
        self.ensure_one()
        record_state = self._fields.get("state") and self.state
        if not record_state:
            return templates
        return templates.filtered(
            lambda template: template.pba_applies_to_record_state(record_state)
        )

    def _pba_whatsapp_get_template_options(self):
        self.ensure_one()
        if not self._pba_whatsapp_record_is_eligible():
            return self.env["mail.whatsapp.template"]
        templates = self._pba_whatsapp_search_model_templates()
        return self._pba_whatsapp_filter_templates_by_record(templates)

    def _pba_whatsapp_record_is_eligible(self):
        return True

    def _pba_whatsapp_get_template_send_log(self, template):
        self.ensure_one()
        return self.env["pba.whatsapp.template.send.log"].search(
            [
                ("res_model", "=", self._name),
                ("res_id", "=", self.id),
                ("template_id", "=", template.id),
            ],
            limit=1,
        )

    def _pba_whatsapp_log_template_send(self, template):
        self.ensure_one()
        log = self._pba_whatsapp_get_template_send_log(template)
        vals = {
            "sent_date": fields.Datetime.now(),
            "user_id": self.env.user.id,
        }
        if log:
            log.write(vals)
            return log
        return self.env["pba.whatsapp.template.send.log"].create(
            {
                "res_model": self._name,
                "res_id": self.id,
                "template_id": template.id,
                **vals,
            }
        )

    def _pba_whatsapp_prepare_template_wizard_lines(self):
        self.ensure_one()
        lines = []
        Log = self.env["pba.whatsapp.template.send.log"]
        for sequence, template in enumerate(
            self._pba_whatsapp_get_template_options(), start=1
        ):
            log = Log.search(
                [
                    ("res_model", "=", self._name),
                    ("res_id", "=", self.id),
                    ("template_id", "=", template.id),
                ],
                limit=1,
            )
            body, _variables = template._pba_prepare_body_and_variables(self)
            lines.append(
                (
                    0,
                    0,
                    {
                        "sequence": sequence * 10,
                        "template_id": template.id,
                        "body_preview": body,
                        "send_state": "sent" if log else "pending",
                        "sent_date": log.sent_date if log else False,
                        "sent_user_id": log.user_id.id if log else False,
                    },
                )
            )
        return lines

    def action_pba_whatsapp_open_templates(self):
        self.ensure_one()
        partner = self._whatsapp_get_partner()
        if not partner:
            raise UserError(_("El documento no tiene un contacto asociado."))
        if not (partner.mobile or partner.phone):
            raise UserError(_("El contacto no tiene teléfono ni móvil configurado."))
        if not self._pba_whatsapp_get_template_options():
            raise UserError(
                _("No hay plantillas WhatsApp disponibles para este documento.")
            )
        wizard = self.env["pba.whatsapp.template.send.wizard"].create(
            {
                "res_model": self._name,
                "res_id": self.id,
                "line_ids": self._pba_whatsapp_prepare_template_wizard_lines(),
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("WhatsApp"),
            "res_model": "pba.whatsapp.template.send.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def _whatsapp_get_partner(self):
        if hasattr(self, "partner_id") and self.partner_id:
            return self.partner_id
        return self.env["res.partner"]

    def _whatsapp_get_phone_field_name(self):
        return "whatsapp_phone"

    def _whatsapp_get_gateway(self):
        gateway = self.env.company.whatsapp_gateway_id
        if not gateway:
            gateway = self.env["mail.gateway"].search(
                [("gateway_type", "=", "whatsapp")], limit=1
            )
        if not gateway:
            raise UserError(
                _("No hay un gateway de WhatsApp configurado para la compañía.")
            )
        return gateway

    def _pba_whatsapp_prepare_send(self, template, fallback_body):
        self.ensure_one()
        if template and template.variable_ids:
            body, variables = template._pba_prepare_body_and_variables(self)
            return body, template, variables
        if template:
            return template.body or "", template, None
        return fallback_body, False, None

    def action_whatsapp_send(self, body, template=False, template_variables=None):
        self.ensure_one()
        partner = self._whatsapp_get_partner()
        if not partner:
            raise UserError(_("El documento no tiene un contacto asociado."))
        if not (partner.mobile or partner.phone):
            raise UserError(_("El contacto no tiene teléfono ni móvil configurado."))
        gateway = self._whatsapp_get_gateway()
        ctx = {
            "default_res_model": self._name,
            "default_res_id": self.id,
            "default_number_field_name": self._whatsapp_get_phone_field_name(),
            "default_body": body,
            "default_gateway_id": gateway.id,
            "pba_whatsapp_res_model": self._name,
            "pba_whatsapp_res_id": self.id,
        }
        if template:
            ctx["default_template_id"] = template.id
        if template_variables is not None:
            ctx["whatsapp_template_variables"] = template_variables
        return {
            "type": "ir.actions.act_window",
            "name": _("Enviar WhatsApp"),
            "res_model": "whatsapp.composer",
            "view_mode": "form",
            "target": "new",
            "context": ctx,
        }
