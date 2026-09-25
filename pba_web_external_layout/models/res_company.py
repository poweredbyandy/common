from odoo import models

_STRIPE_MIX = 0.18


class ResCompany(models.Model):
    _inherit = "res.company"

    def _pba_sale_line_stripe_color(self):
        self.ensure_one()
        color = (self.primary_color or "#dc3545").strip().lstrip("#")
        if len(color) == 3:
            color = "".join(channel * 2 for channel in color)
        if len(color) != 6:
            color = "dc3545"
        try:
            channels = tuple(int(color[index : index + 2], 16) for index in (0, 2, 4))
        except ValueError:
            channels = (220, 53, 69)
        mixed = tuple(
            round((1 - _STRIPE_MIX) * 255 + _STRIPE_MIX * channel)
            for channel in channels
        )
        return "#%02x%02x%02x" % mixed
