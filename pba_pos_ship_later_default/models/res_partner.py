from odoo import api, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields_list = list(super()._load_pos_data_fields(config_id))
        for field_name in ("type", "parent_id"):
            if field_name not in fields_list:
                fields_list.append(field_name)
        return fields_list

    @api.model
    def _load_pos_data_domain(self, data):
        domain = super()._load_pos_data_domain(data)
        return domain + [("type", "!=", "delivery")]
