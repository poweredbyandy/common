from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    qr_code = fields.Char(
        string="Product QR Code",
        compute="_compute_qr_code",
        store=True,
        index=True,
        help="Value encoded in the product QR. Uses the barcode, then the "
        "internal reference, then the product identifier. The image is drawn "
        "in the browser.",
    )

    @api.depends("barcode", "default_code")
    def _compute_qr_code(self):
        for product in self:
            product.qr_code = product._get_qr_code_value()

    def _get_qr_code_value(self):
        self.ensure_one()
        if self.barcode:
            return self.barcode
        if self.default_code:
            return self.default_code
        if isinstance(self.id, int):
            return str(self.id)
        return False
