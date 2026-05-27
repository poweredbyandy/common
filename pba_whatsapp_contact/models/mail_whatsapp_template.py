from odoo import api, models


class MailWhatsappTemplate(models.Model):
    _inherit = "mail.whatsapp.template"

    @api.model
    def _pba_ensure_module_templates(self, module, templates, gateway):
        IrModelData = self.env["ir.model.data"]
        created = {}
        for xmlid, vals in templates.items():
            full_xmlid = f"{module}.{xmlid}"
            template = self.env.ref(full_xmlid, raise_if_not_found=False)
            if template:
                if template.gateway_id.id != gateway.id:
                    template.gateway_id = gateway.id
                created[xmlid] = template
                continue
            template = self.create({**vals, "gateway_id": gateway.id})
            IrModelData.create(
                {
                    "name": xmlid,
                    "module": module,
                    "model": "mail.whatsapp.template",
                    "res_id": template.id,
                    "noupdate": True,
                }
            )
            created[xmlid] = template
        return created
