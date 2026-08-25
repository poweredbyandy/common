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
        website_id = self.env.context.get("portal_qr_website_id")
        if website_id:
            website = self.env["website"].browse(website_id).exists()
            if website:
                return website
        template = self.product_tmpl_id
        if "website_id" in template._fields and template.website_id:
            return template.website_id
        return self.env["website"].get_current_website()

    def get_portal_qr_url_for_website(self, website=None):
        self.ensure_one()
        website = website or self._get_product_qr_portal_website()
        if not website:
            return False
        return website._get_product_qr_portal_url(self)

    @api.depends("qr_code", "product_tmpl_id.website_id")
    def _compute_portal_qr_url(self):
        for product in self:
            website = product._get_product_qr_portal_website()
            product.portal_qr_url = (
                website._get_product_qr_portal_url(product) if website else False
            )
