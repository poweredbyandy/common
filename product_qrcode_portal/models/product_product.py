from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    portal_qr_url = fields.Char(
        string="Portal QR URL",
        compute="_compute_portal_qr_url",
        store=True,
        help="Website link encoded in the portal QR. Scanning it follows "
        "the Product QR Portal Action. The image is drawn in the browser.",
    )

    def _get_product_qr_portal_website(self):
        self.ensure_one()
        template = self.product_tmpl_id
        if "website_id" in template._fields and template.website_id:
            return template.website_id
        return self.env["website"].get_current_website()

    @api.depends("qr_code", "product_tmpl_id.website_id")
    def _compute_portal_qr_url(self):
        fallback = self.env["website"].get_current_website()
        for product in self:
            template = product.product_tmpl_id
            website = fallback
            if "website_id" in template._fields and template.website_id:
                website = template.website_id
            product.portal_qr_url = (
                website._get_product_qr_portal_url(product) if website else False
            )
