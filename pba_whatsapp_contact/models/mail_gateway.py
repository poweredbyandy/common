import importlib

from odoo import _, models
from odoo.exceptions import UserError


class MailGateway(models.Model):
    _inherit = "mail.gateway"

    def _pba_whatsapp_template_specs(self):
        specs = []
        installed = set(
            self.env["ir.module.module"]
            .search(
                [
                    ("name", "in", ("pba_whatsapp_sale", "pba_whatsapp_account")),
                    ("state", "=", "installed"),
                ]
            )
            .mapped("name")
        )
        if "pba_whatsapp_sale" in installed:
            templates_mod = importlib.import_module(
                "odoo.addons.pba_whatsapp_sale.models.pba_whatsapp_templates"
            )
            specs.append(
                {
                    "module": "pba_whatsapp_sale",
                    "templates": templates_mod.SALE_TEMPLATES,
                    "company_fields": templates_mod.SALE_COMPANY_FIELDS,
                }
            )
        if "pba_whatsapp_account" in installed:
            templates_mod = importlib.import_module(
                "odoo.addons.pba_whatsapp_account.models.pba_whatsapp_templates"
            )
            specs.append(
                {
                    "module": "pba_whatsapp_account",
                    "templates": templates_mod.ACCOUNT_TEMPLATES,
                    "company_fields": templates_mod.ACCOUNT_COMPANY_FIELDS,
                }
            )
        return specs

    def _pba_create_whatsapp_templates(self, raise_if_empty=True):
        self.ensure_one()
        if self.gateway_type != "whatsapp":
            raise UserError(_("Solo aplica a gateways de tipo WhatsApp."))
        specs = self._pba_whatsapp_template_specs()
        if not specs:
            if raise_if_empty:
                raise UserError(
                    _(
                        "No hay módulos PBA de plantillas instalados. "
                        "Instale pba_whatsapp_sale y/o pba_whatsapp_account."
                    )
                )
            return 0, []
        Template = self.env["mail.whatsapp.template"]
        company_vals = {}
        created_total = 0
        for spec in specs:
            created = Template._pba_ensure_module_templates(
                spec["module"], spec["templates"], self
            )
            created_total += len(created)
            for field_name, xmlid in spec.get("company_fields", {}).items():
                if xmlid in created:
                    company_vals[field_name] = created[xmlid].id
        company = self.company_id or self.env.company
        if company_vals:
            company.write(company_vals)
        return created_total, specs

    def button_pba_create_whatsapp_templates(self):
        self.ensure_one()
        created_total, specs = self._pba_create_whatsapp_templates()
        modules = ", ".join(spec["module"] for spec in specs)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Plantillas PBA"),
                "message": _(
                    "Se verificaron o crearon %s plantilla(s) para: %s."
                )
                % (created_total, modules),
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
