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
        default="mm",
        required=True,
        help="Unit used for QR label width and height. Dots are printer "
        "dots at the configured DPI.",
    )
    qr_label_width = fields.Float(
        string="QR Label Width",
        default=57.0,
        digits=(16, 3),
        required=True,
        help="Physical label width, not including the liner or side gaps.",
    )
    qr_label_height = fields.Float(
        string="QR Label Height",
        default=31.0,
        digits=(16, 3),
        required=True,
        help="Physical label height sent as ^LL, not including the gap. "
        "For 57 x 32 mm labels use 57 x 31 so the printer finds this gap.",
    )
    qr_label_dpi = fields.Integer(
        string="QR Label DPI",
        default=203,
        required=True,
        help="Printer resolution used to convert mm, cm or inches to dots. "
        "Typical Zebra values are 203, 300 or 600.",
    )
    qr_label_width_dots = fields.Integer(
        string="Width (dots)",
        compute="_compute_qr_label_dots",
    )
    qr_label_height_dots = fields.Integer(
        string="Height (dots)",
        compute="_compute_qr_label_dots",
    )
    qr_label_auto_length = fields.Boolean(
        string="Use Printer Label Length",
        default=False,
        help="After Zebra media calibration, the printer measures the gap "
        "and owns the feed length. Label jobs then omit ^LL.",
    )

    @api.depends("qr_label_uom", "qr_label_width", "qr_label_height", "qr_label_dpi")
    def _compute_qr_label_dots(self):
        for company in self:
            width_dots, height_dots = company._get_qr_label_size_dots()
            company.qr_label_width_dots = width_dots
            company.qr_label_height_dots = height_dots

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

    def action_calibrate_qr_label_printer(self):
        self.ensure_one()
        self.qr_label_auto_length = True
        report = self.env.ref("product_qrcode.action_report_product_qr_zpl")
        return report.with_company(self).report_action(
            None,
            data={"zpl_calibrate": True, "company_id": self.id},
            config=False,
        )

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
