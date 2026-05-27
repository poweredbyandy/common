from odoo import _, fields, models
from odoo.exceptions import UserError


class DiscussChannel(models.Model):
    _inherit = "discuss.channel"

    whatsapp_lead_id = fields.Many2one(
        "crm.lead",
        string="Lead WhatsApp",
        copy=False,
        ondelete="set null",
    )
    whatsapp_lead_window_end = fields.Datetime(
        string="Fin ventana lead WhatsApp",
        copy=False,
    )
    whatsapp_assigned_user_id = fields.Many2one(
        "res.users",
        string="Comercial asignado WhatsApp",
        copy=False,
        ondelete="set null",
    )
    whatsapp_crm_lead_ids = fields.One2many(
        "crm.lead",
        "whatsapp_channel_id",
        string="Leads CRM WhatsApp",
    )
    whatsapp_crm_lead_count = fields.Integer(
        compute="_compute_whatsapp_crm_lead_count"
    )

    def _compute_whatsapp_crm_lead_count(self):
        lead_data = self.env["crm.lead"]._read_group(
            [("whatsapp_channel_id", "in", self.ids)],
            ["whatsapp_channel_id"],
            ["__count"],
        )
        counts = {
            channel.id: count for channel, count in lead_data
        }
        for channel in self:
            channel.whatsapp_crm_lead_count = counts.get(channel.id, 0)

    def _get_whatsapp_crm_leads(self):
        self.ensure_one()
        domain = [("whatsapp_channel_id", "=", self.id)]
        if self.whatsapp_lead_id:
            domain = [
                "|",
                ("whatsapp_channel_id", "=", self.id),
                ("id", "=", self.whatsapp_lead_id.id),
            ]
        return self.env["crm.lead"].search(
            domain,
            order="create_date desc, id desc",
        )

    def action_open_whatsapp_crm_leads(self):
        self.ensure_one()
        leads = self._get_whatsapp_crm_leads()
        if not leads:
            raise UserError(_("No hay oportunidades CRM asociadas a esta conversación."))
        if len(leads) == 1:
            return {
                "type": "ir.actions.act_window",
                "name": leads.display_name,
                "res_model": "crm.lead",
                "res_id": leads.id,
                "view_mode": "form",
                "views": [(False, "form")],
                "target": "current",
            }
        return {
            "type": "ir.actions.act_window",
            "name": _("CRM WhatsApp"),
            "res_model": "crm.lead",
            "view_mode": "list,form",
            "views": [
                (self.env.ref("pba_whatsapp_crm.crm_lead_whatsapp_tree_view").id, "list"),
                (False, "form"),
            ],
            "domain": [("whatsapp_channel_id", "=", self.id)],
            "context": {"create": False},
            "target": "current",
        }
