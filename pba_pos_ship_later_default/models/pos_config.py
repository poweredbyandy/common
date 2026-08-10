from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    pba_ship_later_default = fields.Boolean(
        string="Ship Later by Default",
        help="When enabled, Ship Later is always active with today's date. "
        "Clicking the button opens the date picker to change the delivery date.",
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields_list = list(super()._load_pos_data_fields(config_id))
        if fields_list and "pba_ship_later_default" not in fields_list:
            fields_list.append("pba_ship_later_default")
        return fields_list

    def get_limited_partners_loading(self):
        partners = super().get_limited_partners_loading()
        partner_ids = [partner[0] for partner in partners]
        delivery_ids = set(
            self.env["res.partner"]
            .browse(partner_ids)
            .filtered(lambda partner: partner.type == "delivery")
            .ids
        )
        return [partner for partner in partners if partner[0] not in delivery_ids]
