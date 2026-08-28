from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    qr_code = fields.Char(
        string="Product QR Code",
        compute="_compute_qr_code",
        store=True,
    )

    @api.depends("product_variant_ids.qr_code")
    def _compute_qr_code(self):
        self._compute_template_field_from_variant_field("qr_code")
