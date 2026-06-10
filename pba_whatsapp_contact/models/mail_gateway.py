import importlib

import requests
from werkzeug.urls import url_join

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.mail_gateway_whatsapp.models.mail_gateway import BASE_URL

PBA_TEMPLATE_MODULES = ("pba_whatsapp_sale", "pba_whatsapp_account", "pba_whatsapp_contact")
PBA_COMPANY_TEMPLATE_FIELDS = (
    "whatsapp_template_sale_quotation_id",
    "whatsapp_template_sale_confirmed_id",
    "whatsapp_template_delivery_done_id",
    "whatsapp_template_overdue_id",
)


class MailGateway(models.Model):
    _inherit = "mail.gateway"

    def _pba_whatsapp_template_specs(self):
        specs = []
        module_names = ("pba_whatsapp_sale", "pba_whatsapp_account")
        available_modules = set(
            self.env["ir.module.module"]
            .search(
                [
                    ("name", "in", module_names),
                    ("state", "in", ("installed", "to install", "to upgrade")),
                ]
            )
            .mapped("name")
        )
        module_specs = {
            "pba_whatsapp_sale": (
                "odoo.addons.pba_whatsapp_sale.models.pba_whatsapp_templates",
                "SALE_TEMPLATES",
                "SALE_COMPANY_FIELDS",
            ),
            "pba_whatsapp_account": (
                "odoo.addons.pba_whatsapp_account.models.pba_whatsapp_templates",
                "ACCOUNT_TEMPLATES",
                "ACCOUNT_COMPANY_FIELDS",
            ),
        }
        for module_name in module_names:
            if module_name not in available_modules:
                continue
            import_path, templates_attr, company_fields_attr = module_specs[module_name]
            try:
                templates_mod = importlib.import_module(import_path)
            except Exception:
                continue
            specs.append(
                {
                    "module": module_name,
                    "templates": getattr(templates_mod, templates_attr, {}),
                    "company_fields": getattr(templates_mod, company_fields_attr, {}),
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

    def _pba_template_maps_for_import(self):
        self.ensure_one()
        Template = self.env["mail.whatsapp.template"].with_context(active_test=False)
        current_templates = Template.search([("gateway_id", "=", self.id)])
        templates_by_uid = {
            template.template_uid: template
            for template in current_templates
            if template.template_uid
        }
        templates_by_name = {}
        for template in current_templates:
            if not template.template_name:
                continue
            key = (template.template_name, template.language)
            if key not in templates_by_name:
                templates_by_name[key] = template
        return templates_by_uid, templates_by_name

    def _pba_find_template_for_meta_import(
        self, templates_by_uid, templates_by_name, template_data
    ):
        template = templates_by_uid.get(template_data["id"])
        if template:
            return template
        return templates_by_name.get(
            (template_data.get("name"), template_data.get("language"))
        )

    def button_import_whatsapp_template(self):
        self.ensure_one()
        WhatsappTemplate = self.env["mail.whatsapp.template"]
        if not self.whatsapp_account_id:
            raise UserError(
                self.env._("WhatsApp Account is required to import templates.")
            )
        template_url = url_join(
            BASE_URL,
            f"v{self.whatsapp_version}/{self.whatsapp_account_id}/message_templates",
        )
        try:
            meta_request = requests.get(
                template_url,
                headers={"Authorization": f"Bearer {self.token}"},
                timeout=10,
            )
            meta_request.raise_for_status()
            meta_info = meta_request.json()
        except Exception as err:
            raise UserError(str(err)) from err
        templates_by_uid, templates_by_name = self._pba_template_maps_for_import()
        create_vals = []
        for template_data in meta_info.get("data", []):
            ws_template = self._pba_find_template_for_meta_import(
                templates_by_uid, templates_by_name, template_data
            )
            import_vals = WhatsappTemplate._prepare_values_to_import(
                self, template_data
            )
            if ws_template:
                ws_template.write(
                    ws_template._pba_prepare_import_write_vals(
                        import_vals, template_data
                    )
                )
                if ws_template.template_uid:
                    templates_by_uid[ws_template.template_uid] = ws_template
            else:
                create_vals.append(import_vals)
        if create_vals:
            WhatsappTemplate.create(create_vals)
        merged, _removed = self._pba_merge_duplicate_whatsapp_templates(silent=True)
        message = self.env._("Synchronization successfully.")
        if merged:
            message = self.env._(
                "Sincronización completada. Se unificaron %s plantilla(s) duplicada(s)."
            ) % merged
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": self.env._("WhatsApp Templates"),
                "type": "success",
                "message": message,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def _pba_repoint_company_template_fields(self, old_template, new_template):
        Company = self.env["res.company"].sudo()
        for company in Company.search([]):
            vals = {}
            for field_name in PBA_COMPANY_TEMPLATE_FIELDS:
                if field_name not in company._fields:
                    continue
                if company[field_name].id == old_template.id:
                    vals[field_name] = new_template.id
            if vals:
                company.write(vals)

    def _pba_merge_duplicate_whatsapp_templates(self, silent=False):
        self.ensure_one()
        Template = self.env["mail.whatsapp.template"].with_context(active_test=False)
        templates = Template.search([("gateway_id", "=", self.id)])
        grouped = {}
        for template in templates:
            if not template.template_name:
                continue
            key = (template.template_name, template.language)
            grouped.setdefault(key, []).append(template)
        merged = 0
        for group in grouped.values():
            if len(group) < 2:
                continue
            managed = [template for template in group if template._pba_is_managed_template()]
            if managed:
                keeper = managed[0]
            else:
                approved = [template for template in group if template.state == "approved"]
                keeper = approved[0] if approved else group[0]
            for donor in group:
                if donor.id == keeper.id:
                    continue
                merge_vals = {}
                if donor.template_uid and not keeper.template_uid:
                    merge_vals["template_uid"] = donor.template_uid
                if donor.state == "approved" and keeper.state != "approved":
                    merge_vals["state"] = donor.state
                if merge_vals:
                    keeper.write(merge_vals)
                self._pba_repoint_company_template_fields(donor, keeper)
                donor.unlink()
                merged += 1
        if not silent and not merged:
            return self._pba_notify_template_merge(0)
        return merged, grouped

    def _pba_notify_template_merge(self, merged):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Plantillas PBA"),
                "message": (
                    _("Se unificaron %s plantilla(s) duplicada(s).") % merged
                    if merged
                    else _("No se encontraron plantillas duplicadas.")
                ),
                "type": "success" if merged else "info",
                "sticky": False,
            },
        }

    def button_pba_merge_duplicate_whatsapp_templates(self):
        self.ensure_one()
        if self.gateway_type != "whatsapp":
            raise UserError(_("Solo aplica a gateways de tipo WhatsApp."))
        merged, _grouped = self._pba_merge_duplicate_whatsapp_templates(silent=True)
        return self._pba_notify_template_merge(merged)
