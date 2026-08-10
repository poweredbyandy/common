from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_pba_seller_pos = fields.Boolean(
        related="pos_config_id.pba_seller_pos",
        readonly=False,
    )
    pos_has_active_session = fields.Boolean(
        compute="_compute_pos_has_active_session",
    )

    @api.depends(
        "pos_config_id",
        "pos_config_id.has_active_session",
        "pos_config_id.pba_seller_pos",
    )
    def _compute_pos_has_active_session(self):
        for settings in self:
            config = settings.pos_config_id
            settings.pos_has_active_session = bool(
                config
                and config.has_active_session
                and not config.pba_seller_pos
            )
