from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_pba_ship_later_default = fields.Boolean(
        related="pos_config_id.pba_ship_later_default",
        readonly=False,
    )

    @api.onchange("pos_ship_later")
    def _onchange_pos_ship_later_pba_default(self):
        if not self.pos_ship_later:
            self.pos_pba_ship_later_default = False
