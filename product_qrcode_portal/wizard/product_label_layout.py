from odoo import _, fields, models
from odoo.exceptions import UserError


class ProductLabelLayout(models.TransientModel):
    _inherit = "product.label.layout"

    print_format = fields.Selection(
        selection_add=[
            ("qr_label_url", "ZPL QR (portal URL)"),
        ],
        ondelete={"qr_label_url": "set default"},
    )
    portal_qr_website_id = fields.Many2one(
        comodel_name="website",
        string="Portal QR Website",
        default=lambda self: self.env["website"].get_current_website().id,
        help="Website domain and company encoded in the portal QR URL.",
    )

    def _prepare_report_data(self):
        self.ensure_one()
        if self.print_format == "qr_label_url":
            website = self.portal_qr_website_id or self.env["website"].get_current_website()
            if not website:
                raise UserError(_("Select a website for the portal QR URL."))
            if self.product_tmpl_ids:
                products = self.product_tmpl_ids.mapped("product_variant_ids")
            elif self.product_ids:
                products = self.product_ids
            else:
                raise UserError(
                    _(
                        "No product to print. If the product is archived, "
                        "unarchive it before printing its label."
                    )
                )
            if not products:
                raise UserError(_("No product variants found to print."))
            missing = products.filtered(
                lambda product: not website._get_product_qr_portal_url(product)
            )
            if missing:
                raise UserError(
                    _("Portal QR URL is not available for: %s")
                    % ", ".join(missing.mapped("display_name"))
                )
            data = self._prepare_qr_label_report_data(
                "portal",
                extra_data={"portal_qr_website_id": website.id},
            )
            return "product_qrcode.action_report_product_qr_zpl", data
        return super()._prepare_report_data()
