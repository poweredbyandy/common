from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

QR_LABEL_UOM_SELECTION = [
    ("mm", "Millimeters (mm)"),
    ("cm", "Centimeters (cm)"),
    ("in", "Inches (in)"),
    ("dots", "Dots"),
]


class ResCompany(models.Model):
    _inherit = "res.company"

    qr_label_logo = fields.Image(
        string="QR Label Logo",
        max_width=512,
        max_height=512,
        help="Logo printed on ZPL product QR labels. If empty, the company "
        "logo is used.",
    )
    qr_label_uom = fields.Selection(
        selection=QR_LABEL_UOM_SELECTION,
        string="QR Label Size Unit",
        default="dots",
        required=True,
        help="Unit used for QR label width and height. Dots are printer "
        "dots at the configured DPI.",
    )
    qr_label_width = fields.Float(
        string="QR Label Width",
        default=600.0,
        digits=(16, 3),
        required=True,
        help="Physical label width, not including the liner or side gaps.",
    )
    qr_label_height = fields.Float(
        string="QR Label Height",
        default=300.0,
        digits=(16, 3),
        required=True,
        help="Physical label height, not including the gap between labels. "
        "If a single print feeds an extra blank label, reduce this value "
        "by about 1 mm.",
    )
    qr_label_dpi = fields.Integer(
        string="QR Label DPI",
        default=203,
        required=True,
        help="Printer resolution used to convert mm, cm or inches to dots. "
        "Typical Zebra values are 203, 300 or 600.",
    )
    qr_label_feed_adjust = fields.Integer(
        string="QR Label Feed Adjust",
        default=-16,
        help="Dots added to the media feed (^LL). The printed design stays "
        "on the configured height. Use a negative value if a single print "
        "feeds an extra blank label. Typical value: -16.",
    )
    qr_label_width_dots = fields.Integer(
        string="Width (dots)",
        compute="_compute_qr_label_dots",
    )
    qr_label_height_dots = fields.Integer(
        string="Height (dots)",
        compute="_compute_qr_label_dots",
    )
    qr_label_feed_dots = fields.Integer(
        string="Feed (dots)",
        compute="_compute_qr_label_dots",
    )

    @api.depends(
        "qr_label_uom",
        "qr_label_width",
        "qr_label_height",
        "qr_label_dpi",
        "qr_label_feed_adjust",
    )
    def _compute_qr_label_dots(self):
        for company in self:
            width_dots, height_dots = company._get_qr_label_size_dots()
            company.qr_label_width_dots = width_dots
            company.qr_label_height_dots = height_dots
            company.qr_label_feed_dots = max(1, height_dots + company.qr_label_feed_adjust)

    @api.constrains("qr_label_width", "qr_label_height", "qr_label_dpi")
    def _check_qr_label_size(self):
        for company in self:
            if company.qr_label_width <= 0 or company.qr_label_height <= 0:
                raise ValidationError(
                    _("QR label width and height must be greater than zero.")
                )
            if company.qr_label_dpi <= 0:
                raise ValidationError(_("QR label DPI must be greater than zero."))

    @api.model
    def _convert_qr_label_value_to_dots(self, value, uom, dpi):
        dpi = int(dpi) or 203
        if uom == "dots":
            dots = value
        elif uom == "in":
            dots = value * dpi
        elif uom == "cm":
            dots = value * 10.0 * dpi / 25.4
        else:
            dots = value * dpi / 25.4
        return max(1, int(round(dots)))

    def _get_qr_label_size_dots(self):
        self.ensure_one()
        return (
            self._convert_qr_label_value_to_dots(
                self.qr_label_width, self.qr_label_uom, self.qr_label_dpi
            ),
            self._convert_qr_label_value_to_dots(
                self.qr_label_height, self.qr_label_uom, self.qr_label_dpi
            ),
        )
