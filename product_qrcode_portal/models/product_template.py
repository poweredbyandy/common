from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    portal_qr_url = fields.Char(
        string="Portal QR URL",
        compute="_compute_portal_qr_url",
    )

    @api.depends("product_variant_ids.portal_qr_url")
    def _compute_portal_qr_url(self):
        self._compute_template_field_from_variant_field("portal_qr_url")
